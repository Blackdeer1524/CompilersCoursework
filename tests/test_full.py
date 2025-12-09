import textwrap
from tests import base

from src.optimizations.licm import LICM
from src.optimizations.sccp import SCCP
from src.optimizations.dce import DCE


class TestEndToEnd(base.TestBase):
    def __init__(self, *args):
        passes = [LICM, SCCP, DCE]
        super().__init__(passes, *args)

    def test_matmul(self):
        src = """
        func mat_vec_mul(mat [64][64]int, vec [64]int, result [64]int) -> void {
            for (let i int = 0; i < 64; i = i + 1) {
                let sum int = 0;
                for (let j int = 0; j < 64; j = j + 1) {
                    sum = sum + mat[i][j] * vec[j];
                }
                result[i] = sum;
            }
        }
        """

        expected_ir = textwrap.dedent("""
        """).strip()

        self.assert_ir(src, expected_ir)

    def test_gauss(self):
        src = """
        func gauss_solve(A [64][64]int, b [64]int, x [64]int) -> int {
            for (let i int = 0; i < 64; i = i + 1) {
                let pivot int = A[i][i];
                if (pivot == 0) {
                    return -1;  // Singular
                }

                for (let j int = i + 1; j < 64; j = j + 1) {
                    let factor int = A[j][i];
                    for (let k int = i; k < 64; k = k + 1) {
                        A[j][k] = A[j][k] * pivot - A[i][k] * factor;
                    }
                    b[j] = b[j] * pivot - b[i] * factor;
                }
            }

            for (let i int = 64 - 1; i >= 0; i = i - 1) {
                let sum int = 0;
                for (let j int = i + 1; j < 64; j = j + 1) {
                    sum = sum + A[i][j] * x[j];
                }
                if (A[i][i] == 0) {
                    return -1; // Singular
                }
                x[i] = (b[i] - sum) / A[i][i];
            }
            return 0;
        }
        """

        expected_ir = textwrap.dedent("""
        """).strip()

        self.assert_ir(src, expected_ir)
