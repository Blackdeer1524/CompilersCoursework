from pprint import pprint
from src.parsing.lexer import Lexer
from src.parsing.parser import Parser
from src.parsing.semantic import SemanticAnalyzer


src = \
"""
func add(x int, y int) -> int {
    return x + y;
}

func main() -> void {
    i int = 0;
    for {
        if (i < 10) {
            i = 2 * i + 1;
        }
        
        b int = add(10, i);
        if (b > 30) {
            break;
        }
    }
}
"""


def main():
    lexer = Lexer(src)
    parser = Parser(lexer)
    program = parser.parse()
    analyzer = SemanticAnalyzer(program)
    errors = analyzer.analyze()
    if errors:
        for error in errors:
            print(error)
    else:
        pprint(program)


if __name__ == "__main__":
    main()
    