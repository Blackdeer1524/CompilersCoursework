import textwrap
import unittest

from src.optimizations.sccp import SCCP
from src.parsing.lexer import Lexer
from src.parsing.parser import Parser
from src.parsing.semantic import SemanticAnalyzer
from src.ssa.cfg import CFG, CFGBuilder
from src.ssa.dominance import compute_dominance_frontier_graph, compute_dominator_tree
from src.ssa.ssa import SSABuilder


class TestSCCP(unittest.TestCase):
    def parse_programm(self, src: str) -> CFG:
        lexer = Lexer(src)
        parser = Parser(lexer)
        ast = parser.parse()
        analyzer = SemanticAnalyzer(ast)

        errors = analyzer.analyze()
        self.assertListEqual(errors, [])
        
        builder = CFGBuilder()
        cfgs = builder.build(ast)
        self.assertEqual(len(cfgs), 1)
        
        ssa_builder = SSABuilder()
        ssa_builder.build(cfgs[0])
        
        return cfgs[0]

    def make_main(self, prog) -> str:
        return f"func main() -> int {{  {prog}  }}"

    def test_constant_prop(self):
        src = self.make_main("""
        a int = 0;
        return a;
        """)
        
        main = self.parse_programm(src)
        SCCP().run(main)
        ir = main.to_IR().strip()

        expected_ir = textwrap.dedent("""
        BB0: ; [entry]
          a_v1 = 0
          return(0)
        """).strip()

        self.assertEqual(expected_ir, ir)
    
    def test_transition_const(self):
        src = self.make_main("""
            a int = 0;
            b int = a + 10;
            return b;
        """)

        main = self.parse_programm(src)
        SCCP().run(main)
        ir = main.to_IR().strip()

        expected_ir = textwrap.dedent("""
        BB0: ; [entry]
          a_v1 = 0
          b_v1 = 10
          return(10)
        """).strip()

        self.assertEqual(expected_ir, ir)
    
    def test_simple_unreachable_block_drop(self):
        src = self.make_main("""
            a int = 0;
            if (a > 0) {
                a = 10;
            }
            return a;
        """)
        
        main = self.parse_programm(src)
        SCCP().run(main)
        ir = main.to_IR().strip()

        expected_ir = textwrap.dedent("""
        BB0: ; [entry]
          a_v1 = 0
          %0_v1 = 0
          jmp BB3
        
        BB3: ; [merge]
          a_v3 = ϕ(BB0: 0)
          
          return(0)
        """).strip()

        self.assertEqual(expected_ir, ir)
      
    def test_interblock_propogation(self):
        src = self.make_main("""
            a int = 5;
            b int = 10;
            if (a == 5) {
                b = a + 10;  // b = 15
            }
            return b;  // return 15
        """)
        
        main = self.parse_programm(src)
        SCCP().run(main)
        ir = main.to_IR().strip()

        expected_ir = textwrap.dedent("""
            BB0: ; [entry]
              a_v1 = 5
              b_v1 = 10
              %0_v1 = 1
              jmp BB2

            BB2: ; [then]
              b_v2 = 15
              jmp BB3

            BB3: ; [merge]
              b_v3 = ϕ(BB0: 10, BB2: 15)

              return(15)

            BB3: ; [merge]
              b_v3 = ϕ(BB0: 10, BB2: 15)

              return(15)
          """).strip()

        self.assertEqual(expected_ir, ir)

    def test_dead_cycle(self):
        src = self.make_main("""
            N int = 0;
            for (i int = 0; i < N; i = i + 1) { 
                N = (N + 1) * 2;
            }
            return N; // 0 
        """)

        main = self.parse_programm(src)
        SCCP().run(main)
        ir = main.to_IR().strip()

        expected_ir = textwrap.dedent("""
            BB0: ; [entry]
              N_v1 = 0
              jmp BB2

            BB2: ; [loop init]
              i_v1 = 0
              jmp BB3

            BB3: ; [loop header]
              N_v2 = ϕ(BB2: 0)
              i_v2 = ϕ(BB2: 0)

              %0_v1 = 0
              jmp BB4

            BB4: ; [loop exit]
              return(0)"""
        ).strip()

        self.assertEqual(expected_ir, ir)
    
    def test_initially_dead_condition(self):
        src = self.make_main("""
            N int = 0;
            for (i int = 0; i < 10; i = i + 1) {
                if (N > 10) { // is initially considered as unreachable
                    break;  
                }
                N = (N + 1) * 2;
            }
            return N;
        """)

        main = self.parse_programm(src)
        SCCP().run(main)
        ir = main.to_IR().strip()

        expected_ir = textwrap.dedent("""
            BB0: ; [entry]
              N_v1 = 0
              jmp BB2

            BB2: ; [loop init]
              i_v1 = 0
              jmp BB3

            BB3: ; [loop header]
              N_v2 = ϕ(BB2: 0, BB6: N_v3)
              i_v2 = ϕ(BB2: 0, BB6: i_v3)

              %0_v1 = i_v2 < 10
              cmp(%0_v1, 1)
              if CF == 1 then jmp BB5 else jmp BB4

            BB4: ; [loop exit]
              return(N_v2)

            BB5: ; [loop body]
              %3_v1 = N_v2 > 10
              cmp(%3_v1, 1)
              if CF == 1 then jmp BB7 else jmp BB8

            BB7: ; [then]
              jmp BB4

            BB8: ; [merge]
              %6_v1 = N_v2 + 1
              N_v3 = %6_v1 * 2
              jmp BB6

            BB6: ; [loop update]
              i_v3 = i_v2 + 1
              jmp BB3
        """).strip()

        if expected_ir != ir:
          idom_tree = compute_dominator_tree(main)
          df = compute_dominance_frontier_graph(main, idom_tree)
          graph = main.to_graphviz(idom_tree.reversed_idom, df)
          self.assertEqual(expected_ir, ir, graph)
          
    def test_break_on_first_iter(self):
        src = self.make_main("""
            N int = 0;
            for (i int = 0; i < 10; i = i + 1) {
                if (N < 10) { 
                    break;  
                }
                N = (N + 1) * 2;
            }
            return N;
        """)

        main = self.parse_programm(src)
        SCCP().run(main)
        ir = main.to_IR().strip()

        expected_ir = textwrap.dedent("""
            ???
        """).strip()

        if expected_ir != ir:
          idom_tree = compute_dominator_tree(main)
          df = compute_dominance_frontier_graph(main, idom_tree)
          graph = main.to_graphviz(idom_tree.reversed_idom, df)
          self.assertEqual(expected_ir, ir, graph)
        

        
