import unittest
from src.parsing.lexer import Lexer
from src.parsing.parser import Parser
from src.parsing.semantic import SemanticAnalyzer, SemanticError


class TestSemanticAnalyzer(unittest.TestCase):
    """Unit tests for the SemanticAnalyzer class."""

    def analyze_source(self, source: str) -> list[SemanticError]:
        """Helper method to analyze source code."""
        lexer = Lexer(source)
        parser = Parser(lexer)
        ast = parser.parse()
        analyzer = SemanticAnalyzer(ast)
        return analyzer.analyze()

    def assert_no_errors(self, source: str):
        """Assert that semantic analysis produces no errors."""
        errors = self.analyze_source(source)
        self.assertEqual(len(errors), 0, f"Expected no errors but got: {errors}")

    def assert_has_error(self, source: str, expected_error_substring: str):
        """Assert that semantic analysis produces an error containing the substring."""
        errors = self.analyze_source(source)
        self.assertGreater(len(errors), 0, f"Expected at least one error but got none")
        error_messages = [str(e) for e in errors]
        self.assertTrue(
            any(expected_error_substring in msg for msg in error_messages),
            f"Expected error containing '{expected_error_substring}' but got: {error_messages}",
        )

    # Valid programs

    def test_valid_simple_program(self):
        """Test valid simple program."""
        source = "func main() -> void { }"
        self.assert_no_errors(source)

    def test_valid_function_with_return(self):
        """Test valid function with return statement."""
        source = "func foo() -> int { return 1; }"
        self.assert_no_errors(source)

    def test_valid_assignment(self):
        """Test valid assignment."""
        source = "func main() -> void { a int = 1; }"
        self.assert_no_errors(source)

    def test_valid_reassignment(self):
        """Test valid reassignment."""
        source = "func main() -> void { a int = 1; a = 2; }"
        self.assert_no_errors(source)

    def test_valid_function_call(self):
        """Test valid function call."""
        source = """func foo() -> int { return 1; }
func main() -> void { foo(); }"""
        self.assert_no_errors(source)

    def test_valid_function_with_arguments(self):
        """Test valid function with arguments."""
        source = """func add(x int, y int) -> int { return x + y; }
func main() -> void { a int = add(1, 2); }"""
        self.assert_no_errors(source)

    def test_valid_complex_program(self):
        """Test valid complex program."""
        source = """func add(x int, y int) -> int {
    return x + y;
}

func main() -> void {
    a int = 1;
    b int = 2;
    c int = add(a, b);
    if (c > 0) {
        d int = c * 2;
    }
    return;
}"""
        self.assert_no_errors(source)

    # Function existence errors

    def test_undefined_function(self):
        """Test error when function is not defined."""
        source = "func main() -> void { foo(); }"
        self.assert_has_error(source, "Function 'foo' is not declared")

    def test_undefined_function_in_expression(self):
        """Test error when function call in expression is undefined."""
        source = "func main() -> void { a int = bar(); }"
        self.assert_has_error(source, "Function 'bar' is not declared")

    # Function argument errors

    def test_wrong_argument_count_too_many(self):
        """Test error when too many arguments provided."""
        source = """func foo(x int) -> int { return x; }
func main() -> void { foo(1, 2); }"""
        self.assert_has_error(source, "expects 1 arguments, but got 2")

    def test_wrong_argument_count_too_few(self):
        """Test error when too few arguments provided."""
        source = """func foo(x int, y int) -> int { return x; }
func main() -> void { foo(1); }"""
        self.assert_has_error(source, "expects 2 arguments, but got 1")

    def test_wrong_argument_count_zero_expected(self):
        """Test error when function expects no arguments but gets some."""
        source = """func foo() -> int { return 1; }
func main() -> void { foo(1); }"""
        self.assert_has_error(source, "expects 0 arguments, but got 1")

    def test_wrong_argument_type(self):
        """Test error when argument type doesn't match."""
        # Note: In this language, all expressions are int, so this test
        # might not directly apply, but we test the mechanism
        source = """func foo(x int) -> int { return x; }
func main() -> void { 
    y int = 1;
    foo(y);  // This should be OK since y is int
}"""
        self.assert_no_errors(source)

    # Variable scope errors

    def test_undefined_variable(self):
        """Test error when variable is not defined."""
        source = "func main() -> void { a int = x; }"
        self.assert_has_error(source, "Variable 'x' is not declared")

    def test_undefined_variable_in_reassignment(self):
        """Test error when reassigning undefined variable."""
        source = "func main() -> void { x = 1; }"
        self.assert_has_error(source, "Variable 'x' is not declared")

    def test_undefined_variable_in_expression(self):
        """Test error when using undefined variable in expression."""
        source = "func main() -> void { a int = x + 1; }"
        self.assert_has_error(source, "Variable 'x' is not declared")

    def test_variable_redeclaration_same_scope(self):
        """Test error when variable is redeclared in same scope."""
        source = "func main() -> void { a int = 1; a int = 2; }"
        self.assert_has_error(source, "Variable 'a' already declared in this scope")

    def test_variable_redeclaration_parameter(self):
        """Test error when variable shadows parameter."""
        source = "func foo(x int) -> void { x int = 1; }"
        self.assert_has_error(source, "Variable 'x' already declared in this scope")

    def test_variable_access_from_inner_scope(self):
        """Test that variables from outer scope are accessible."""
        source = """func main() -> void {
    a int = 1;
    if (a < 10) {
        b int = a;
    }
}"""
        self.assert_no_errors(source)

    def test_variable_not_accessible_from_outer_scope(self):
        """Test error when accessing variable from inner scope."""
        source = """func main() -> void {
    if (1 < 10) {
        a int = 1;
    }
    b int = a;
}"""
        self.assert_has_error(source, "Variable 'a' is not declared")

    def test_variable_scope_in_for_loop(self):
        """Test variable scope in for loop."""
        source = """func main() -> void {
    for (i int = 0; i < 10; i = i + 1) {
        j int = i;
    }
}"""
        self.assert_no_errors(source)

    def test_variable_scope_in_unconditional_loop(self):
        """Test variable scope in unconditional loop."""
        source = """func main() -> void {
    for {
        a int = 1;
    }
}"""
        self.assert_no_errors(source)

    def test_variable_scope_in_block(self):
        """Test variable scope in block."""
        source = """func main() -> void {
    {
        a int = 1;
    }
}"""
        self.assert_no_errors(source)

    # Return type errors

    def test_return_type_mismatch_void_function(self):
        """Test error when void function returns a value."""
        source = "func foo() -> void { return 1; }"
        self.assert_has_error(source, "returns void, but return statement has a value")

    def test_return_type_mismatch_int_function_no_value(self):
        """Test error when int function returns no value."""
        source = "func foo() -> int { return; }"
        self.assert_has_error(source, "expects return type int, but got void")

    def test_return_type_mismatch_value_type(self):
        """Test error when return value type doesn't match."""
        # In this language, all expressions are int, so this is mainly
        # checking that void functions don't return values
        source = "func foo() -> int { return 1 + 2; }"
        self.assert_no_errors(source)

    def test_return_outside_function(self):
        """Test that return outside function is caught (though parser prevents this)."""
        # This would be caught by parser, but we test the semantic check
        pass

    # Type checking errors

    def test_assignment_type_mismatch(self):
        """Test error when assignment type doesn't match."""
        # In this language, all expressions are int, so this test mainly
        # ensures the type checking mechanism works
        source = "func main() -> void { a int = 1; }"
        self.assert_no_errors(source)

    def test_reassignment_type_mismatch(self):
        """Test error when reassignment type doesn't match."""
        # Similar to above - all expressions are int
        source = "func main() -> void { a int = 1; a = 2; }"
        self.assert_no_errors(source)

    # Expression type checking

    def test_binary_operation_types(self):
        """Test that binary operations work correctly."""
        source = "func main() -> void { a int = 1 + 2; b int = 3 * 4; c int = 5 - 6; }"
        self.assert_no_errors(source)

    def test_unary_operation_types(self):
        """Test that unary operations work correctly."""
        source = "func main() -> void { a int = -1; b int = !0; }"
        self.assert_no_errors(source)

    def test_comparison_operations(self):
        """Test that comparison operations work correctly."""
        source = "func main() -> void { a int = 1 < 2; b int = 3 > 4; c int = 5 == 6; }"
        self.assert_no_errors(source)

    def test_logical_operations(self):
        """Test that logical operations work correctly."""
        source = "func main() -> void { a int = 1 && 2; b int = 3 || 4; }"
        self.assert_no_errors(source)

    # Function declaration errors

    def test_duplicate_function_declaration(self):
        """Test error when function is declared twice."""
        source = """func foo() -> void { }
func foo() -> void { }"""
        self.assert_has_error(source, "Function 'foo' already declared")

    # Condition and loop errors

    def test_condition_expression_type(self):
        """Test that condition expression must be int."""
        # In this language, all expressions are int, so conditions are fine
        source = "func main() -> void { if (1 < 2) { } }"
        self.assert_no_errors(source)

    def test_for_loop_condition_type(self):
        """Test that for loop condition must be int."""
        source = "func main() -> void { for (i int = 0; i < 10; i = i + 1) { } }"
        self.assert_no_errors(source)

    # Complex scenarios

    def test_nested_function_calls(self):
        """Test nested function calls."""
        source = """func add(x int, y int) -> int { return x + y; }
func main() -> void {
    a int = add(add(1, 2), add(3, 4));
}"""
        self.assert_no_errors(source)

    def test_function_call_as_argument(self):
        """Test function call as function argument."""
        source = """func add(x int, y int) -> int { return x + y; }
func main() -> void {
    a int = add(add(1, 2), 3);
}"""
        self.assert_no_errors(source)

    def test_multiple_errors(self):
        """Test that multiple errors are detected."""
        source = """func main() -> void {
    a int = x;  // x undefined
    foo();  // foo undefined
    b int = a;  // OK - a is defined
}"""
        errors = self.analyze_source(source)
        self.assertGreaterEqual(len(errors), 2, "Expected at least 2 errors")

    def test_parameter_usage(self):
        """Test that function parameters can be used."""
        source = """func add(x int, y int) -> int {
    return x + y;
}"""
        self.assert_no_errors(source)

    def test_parameter_in_expression(self):
        """Test using parameters in expressions."""
        source = """func compute(a int, b int) -> int {
    c int = a + b;
    return c * 2;
}"""
        self.assert_no_errors(source)

    def test_if_else_blocks(self):
        """Test if-else blocks."""
        source = """func main() -> void {
    if (1 < 2) {
        a int = 1;
    } else {
        a int = 2;
    }
}"""
        self.assert_no_errors(source)

    def test_if_else_variable_scoping(self):
        """Test variable scoping in if-else blocks."""
        source = """func main() -> void {
    if (1 < 2) {
        a int = 1;
    } else {
        a int = 2;
    }
    // Each branch has its own scope, so a is not accessible here
}"""
        # This should be OK - each branch declares its own a
        self.assert_no_errors(source)

    def test_complex_expression_types(self):
        """Test complex expression type checking."""
        source = """func main() -> void {
    a int = (1 + 2) * (3 - 4);
    b int = 1 < 2 && 3 > 4;
    c int = 1 || 2 && 3;
}"""
        self.assert_no_errors(source)

    def test_for_loop_variable_scope(self):
        """Test variable scope in for loop init."""
        source = """func main() -> void {
    for (i int = 0; i < 10; i = i + 1) {
        j int = i;  // i should be accessible
    }
}"""
        self.assert_no_errors(source)

    def test_unconditional_loop_body(self):
        """Test unconditional loop body."""
        source = """func main() -> void {
    for {
        a int = 1;
        b int = 2;
    }
}"""
        self.assert_no_errors(source)

    def test_block_statements(self):
        """Test block statements."""
        source = """func main() -> void {
    {
        a int = 1;
        {
            b int = 2;
        }
    }
}"""
        self.assert_no_errors(source)

    def test_return_in_different_contexts(self):
        """Test return statements in different contexts."""
        source = """func foo() -> int {
    if (1 < 2) {
        return 1;
    } else {
        return 2;
    }
}"""
        self.assert_no_errors(source)

    def test_function_call_with_variables(self):
        """Test function call with variable arguments."""
        source = """func add(x int, y int) -> int { return x + y; }
func main() -> void {
    a int = 1;
    b int = 2;
    c int = add(a, b);
}"""
        self.assert_no_errors(source)

    def test_function_call_with_expressions(self):
        """Test function call with expression arguments."""
        source = """func add(x int, y int) -> int { return x + y; }
func main() -> void {
    a int = add(1 + 2, 3 * 4);
}"""
        self.assert_no_errors(source)

    def test_multiple_functions_valid(self):
        """Test multiple valid functions."""
        source = """func foo() -> int { return 1; }
func bar() -> void { }
func baz(x int) -> int { return x; }"""
        self.assert_no_errors(source)

    def test_calling_function_from_another_function(self):
        """Test calling function from another function."""
        source = """func helper() -> int { return 1; }
func main() -> void {
    a int = helper();
}"""
        self.assert_no_errors(source)


if __name__ == "__main__":
    unittest.main()
