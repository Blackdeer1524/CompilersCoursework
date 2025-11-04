from abc import ABC
from dataclasses import dataclass, field
from typing import Optional
from src.parsing.parser import (
    Program, Function, Statement, Assignment, Reassignment,
    Condition, ForLoop, UnconditionalLoop, FunctionCall, Return, Break, Continue, Block,
    Expression, BinaryOp, UnaryOp, Identifier, IntegerLiteral, CallExpression
)

    
@dataclass
class SSAValue:
    name: str
    
    def __repr__(self):
        return self.name

class Operation(ABC):
    ...

@dataclass
class OpStore(Operation):
    value: int
    
    def __repr__(self):
        return f"store({self.value})"
    
@dataclass
class OpCall(Operation): 
    name: str
    args: list['SSAValue']
    
    def __repr__(self):
        args_str = ", ".join(repr(arg) for arg in self.args)
        return f"{self.name}({args_str})"

@dataclass
class OpBinary(Operation):
    type: str
    op1: 'SSAValue'
    op2: 'SSAValue'
    
    def __repr__(self):
        return f"{self.op1} {self.type} {self.op2}"

@dataclass
class OpUnary(Operation):
    type: str
    op: 'SSAValue'
    
    def __repr__(self):
        return f"{self.type}{self.op}"

@dataclass
class Instruction(ABC):
    ...

@dataclass
class InstAssign(Instruction):
    lhs: SSAValue
    rhs: Operation
    
    def __repr__(self):
        return f"{self.lhs} = {self.rhs}"

@dataclass
class InstCmp(Instruction):
    left: SSAValue
    right: SSAValue
    
    def __repr__(self):
        return f"cmp({self.left}, {self.right})"

@dataclass
class InstJump(Instruction):
    kind: str
    label: str
    
    def __repr__(self):
        return f"jump({self.kind}, {self.label})"


@dataclass
class InstReturn(Instruction):
    value: Optional[SSAValue]
    
    def __repr__(self):
        if self.value is None:
            return "return"
        return f"return({self.value})"
    

@dataclass
class OpPhi(Instruction):
    lhs: 'SSAValue'
    rhs: dict[str, 'SSAValue']  # Basic Block name -> corresponding SSAValue
    
    def __repr__(self):
        rhs_str = ", ".join(f"{bb}: {val}" for bb, val in self.rhs.items())
        return f"{self.lhs} = phi({rhs_str})"


class BasicBlock:
    def __init__(self, label: str):
        self.label = label
        self.instructions: list[Instruction] = []
        self.phi_nodes: dict[str, OpPhi] = {}
        self.preds: list['BasicBlock'] = []
        self.succ: list['BasicBlock'] = []

    def insert_phi(self, name: str):
        if self.phi_nodes.get(name) is None:
            self.phi_nodes[name] = OpPhi(SSAValue(name), {})

    def append(self, inst: Instruction):
        self.instructions.append(inst)
    
    def add_child(self, bb: 'BasicBlock'):
        if bb not in self.succ:
            self.succ.append(bb)
        if self not in bb.preds:
            bb.preds.append(self)
    
    def add_pred(self, bb: 'BasicBlock'):
        if bb not in self.preds:
            self.preds.append(bb)
        if self not in bb.succ:
            bb.succ.append(self)


@dataclass
class CFG:
    """Control Flow Graph for a function."""
    entry: BasicBlock
    exit: BasicBlock
    blocks: list[BasicBlock]
    
    def get_block_by_name(self, name: str) -> Optional[BasicBlock]:
        """Get a basic block by name."""
        for bb in self.blocks:
            if bb.label == name:
                return bb
        return None


class CFGBuilder:
    """Builds Control Flow Graphs from AST."""
    
    def __init__(self):
        self.block_counter = 0
        self.tmp_var_counter = 0
        self.current_block: Optional[BasicBlock] = None
        self.break_targets: list[BasicBlock] = []  # Stack of break targets
        self.continue_targets: list[BasicBlock] = []  # Stack of continue targets
    
    def _get_tmp_var_name(self) -> SSAValue:
        name = SSAValue(f"%{self.tmp_var_counter}") 
        self.tmp_var_counter += 1
        return name
    
    def _new_block(self, name: Optional[str] = None) -> BasicBlock:
        """Create a new basic block with a unique name."""
        if name is None:
            name = f"bb{self.block_counter}"
            self.block_counter += 1
        bb = BasicBlock(name)
        return bb
    
    def _switch_to_block(self, bb: BasicBlock):
        """Switch to a different basic block."""
        self.current_block = bb
    
    def build(self, program: Program) -> dict[str, CFG]:
        """Build CFG for each function in the program.
        
        Returns:
            Dictionary mapping function names to their CFGs.
        """
        cfgs = {}
        for func in program.functions:
            cfg = self._build_function(func)
            cfgs[func.name] = cfg
        return cfgs
    
    def _build_function(self, func: Function) -> CFG:
        """Build CFG for a single function."""
        self.block_counter = 0
        self.break_targets = []
        self.continue_targets = []
        
        # Create entry and exit blocks
        entry = self._new_block("entry")
        exit_block = self._new_block("exit")
        
        cfg = CFG(entry=entry, exit=exit_block, blocks=[entry, exit_block])
        self.current_cfg = cfg
        self.current_block = entry
        
        # Build CFG for function body
        self._build_block(func.body)
        
        # Connect current block to exit if it doesn't already have successors
        if not self.current_block.succ:
            self.current_block.add_child(exit_block)
        
        return cfg
    
    def _build_block(self, block: Block):
        """Build CFG for a block of statements."""
        for stmt in block.statements:
            self._build_statement(stmt)
    
    def _build_statement(self, stmt: Statement):
        """Build CFG for a statement."""
        match stmt:
            case Assignment():
                self._build_assignment(stmt)
            case Reassignment():
                self._build_reassignment(stmt)
            case Condition():
                self._build_condition(stmt)
            case ForLoop():
                self._build_for_loop(stmt)
            case UnconditionalLoop():
                self._build_unconditional_loop(stmt)
            case FunctionCall():
                self._build_function_call(stmt)
            case Return():
                self._build_return(stmt)
            case Break():
                self._build_break(stmt)
            case Continue():
                self._build_continue(stmt)
            case Block():
                self._build_block(stmt)
    
    def _build_assignment(self, stmt: Assignment):
        assert self.current_block is not None, "Current block must be set"
        _ = self._build_sub_expression(stmt.value, SSAValue(stmt.name))
    
    def _build_sub_expression(self, expr: Expression, name: SSAValue) -> SSAValue:
        assert self.current_block is not None, "Current block must be set"

        match expr:
            case BinaryOp(op, left, right):
                l = self._build_sub_expression(left, self._get_tmp_var_name())
                r = self._build_sub_expression(right, self._get_tmp_var_name())
                self.current_block.append(
                    InstAssign(name, OpBinary(op, l, r))
                )
                return name
            case UnaryOp(op, operand):
                subexpr_val = self._build_sub_expression(operand, self._get_tmp_var_name())
                self.current_block.append(InstAssign(name, OpUnary(op, subexpr_val)))
                return name
            case Identifier(ident_name):
                return SSAValue(ident_name)
            case IntegerLiteral(value):
                self.current_block.append(InstAssign(name, OpStore(value)))
                return name
            case CallExpression(func_name, args):
                args = [self._build_sub_expression(arg, self._get_tmp_var_name()) for arg in args]
                self.current_block.append(InstAssign(name, OpCall(func_name, args)))
                return name
            case _:
                raise ValueError(f"Unknown expression type: {type(expr).__name__}")
    
    def _build_reassignment(self, stmt: Reassignment):
        assert self.current_block is not None, "Current block must be set"
        _ = self._build_sub_expression(stmt.value, SSAValue(stmt.name))
    
    def _build_function_call(self, stmt: FunctionCall):
        assert self.current_block is not None, "Current block must be set"
        tmp = self._get_tmp_var_name()
        args = [self._build_sub_expression(arg, self._get_tmp_var_name()) for arg in stmt.args]
        self.current_block.append(InstAssign(tmp, OpCall(stmt.name, args)))
    
    def _build_condition(self, stmt: Condition):
        assert self.current_block is not None, "Current block must be set"
        
        then_block = self._new_block()
        merge_block = self._new_block()
        
        zero_var = self._get_tmp_var_name()
        self.current_block.append(InstAssign(zero_var, OpStore(0)))
        cond_var = self._build_sub_expression(stmt.condition, self._get_tmp_var_name())
        self.current_block.append(InstCmp(cond_var, zero_var))
        self.current_block.append(InstJump("jnz", then_block.label))
        
        if stmt.else_block is None:
            self.current_block.append(InstJump("jz", merge_block.label))
        else:
            else_block = self._new_block()
            self.current_block.append(InstJump("jz", else_block.label))
            self.current_block.add_child(else_block)

            old_block = self.current_block
            self._switch_to_block(else_block)
            self._build_block(stmt.else_block)

            self.current_block.add_child(merge_block)
            self.current_block.append(InstJump("jmp", merge_block.label))
            self._switch_to_block(old_block)


        self.current_block.add_child(then_block)
        self._switch_to_block(then_block)
        self._build_block(stmt.then_block)
        
        self.current_block.add_child(merge_block)
        self.current_block.append(InstJump("jmp", merge_block.label))
        self._switch_to_block(merge_block)
    
    def _build_for_loop(self, stmt: ForLoop):
        assert self.current_block is not None, "Current block must be set"
        
        init_block = self._new_block()
        header_block = self._new_block()
        body_block = self._new_block()
        update_block = self._new_block()
        exit_block = self._new_block()
        
        self.break_targets.append(exit_block)
        self.continue_targets.append(update_block)
        
        self.current_block.add_child(init_block)
        self.current_block.append(InstJump("jmp", init_block.label))

        self._switch_to_block(init_block) 
        self.current_block.add_child(header_block)
        zero_var = self._get_tmp_var_name()
        self.current_block.append(InstAssign(zero_var, OpStore(0)))
        self.current_block.append(InstJump("jmp", header_block.label))
        
        self._switch_to_block(header_block)
        self.current_block.add_child(body_block) 
        self.current_block.add_child(exit_block)
        cond_var = self._build_sub_expression(stmt.condition, self._get_tmp_var_name())
        self.current_block.append(InstCmp(cond_var, zero_var))
        self.current_block.append(InstJump("jnz", body_block.label))
        self.current_block.append(InstJump("jmp", exit_block.label))
        
        self._switch_to_block(body_block)
        self._build_block(stmt.body)
        
        self.current_block.add_child(update_block)
        self.current_block.append(InstJump("jmp", update_block.label))
        
        self._switch_to_block(update_block)
        self.current_block.add_child(header_block)
        self._build_reassignment(stmt.update)
        self.current_block.append(InstJump("jmp", header_block.label))
        
        self.break_targets.pop()
        self.continue_targets.pop()
        self._switch_to_block(exit_block)
    
    def _build_unconditional_loop(self, stmt: UnconditionalLoop):
        """Build CFG for unconditional loop."""
        assert self.current_block is not None, "Current block must be set"
        
        init_block = self._new_block()
        body_block = self._new_block()
        exit_block = self._new_block()
        
        self.break_targets.append(exit_block)
        self.continue_targets.append(init_block)
        
        self.current_block.add_child(init_block)
        self.current_block.append(InstJump("jmp", init_block.label))
        
        self._switch_to_block(init_block)
        self.current_block.add_child(body_block)
        self.current_block.append(InstJump("jmp", body_block.label))
        
        self._switch_to_block(body_block)
        self._build_block(stmt.body)
        
        self.current_block.add_child(init_block)
        self.current_block.append(InstJump("jmp", body_block.label))
        
        self.break_targets.pop()
        self.continue_targets.pop()
        
        self._switch_to_block(exit_block)
    
    def _build_return(self, stmt: Return):
        """Build CFG for return statement."""
        assert self.current_block is not None, "Current block must be set"
        assert self.current_cfg is not None, "Current CFG must be set"

        if stmt.value is not None:
            ret_ssa = self._build_sub_expression(stmt.value, self._get_tmp_var_name())
            self.current_block.append(InstReturn(ret_ssa))
        else:
            self.current_block.append(InstReturn(None))

        self.current_block.add_child(self.current_cfg.exit)
        self._switch_to_block(self._new_block())
    
    def _build_break(self, stmt: Break):
        """Build CFG for break statement."""
        assert self.current_block is not None, "Current block must be set"
        
        assert self.break_targets
        if self.break_targets:
            target = self.break_targets[-1]
            self.current_block.add_child(target)
            self.current_block.append(InstJump("jmp", target.label))
    
    def _build_continue(self, stmt: Continue):
        """Build CFG for continue statement."""
        assert self.current_block is not None, "Current block must be set"
        
        if self.continue_targets:
            target = self.continue_targets[-1]
            self.current_block.add_child(target)
            self.current_block.append(InstJump("jmp", target.label))


if __name__ == "__main__":
    # Test the CFG builder
    from src.parsing.lexer import Lexer
    from src.parsing.parser import Parser
    
    test_code = """func main() -> void {
    a int = 1;
    if (a < 10) {
        b int = 2;
    } else {
        c int = 3;
    }
    for (i int = 0; i < 10; i = i + 1) {
        if (i == 5) {
            break;
        }
    }
    return;
}"""
    
    lexer = Lexer(test_code)
    parser = Parser(lexer)
    ast = parser.parse()
    
    builder = CFGBuilder()
    cfgs = builder.build(ast)
    
    print(f"Built CFG for {len(cfgs)} function(s)")
    for func_name, cfg in cfgs.items():
        print(f"\nFunction: {func_name}")
        print(f"  Entry: {cfg.entry.label}")
        print(f"  Exit: {cfg.exit.label}")
        print(f"  Total blocks: {len(cfg.blocks)}")
        print(f"  Block names: {[bb.label for bb in cfg.blocks]}")
        
        # Print CFG structure
        print("\n  CFG Structure:")
        for bb in cfg.blocks:
            succ_names = [s.label for s in bb.succ]
            pred_names = [p.label for p in bb.preds]
            print(f"    {bb.label}: preds={pred_names}, succs={succ_names}")
