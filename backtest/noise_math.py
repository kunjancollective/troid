"""What chance alone produces when the best of several configurations is picked.

expected_max_normal(k) is E[max of k independent standard normals]: the expected best of k
configurations under a true zero edge, in standard errors. It replaces the asymptotic
sqrt(2 ln k), which overstates it for small k (2.61 against 2.04 at k = 30). ask troid's
trade_math stats computes the same integral the same way (web/api/troid.js).
"""
import math


def expected_max_normal(k: int, h: float = 1e-3, lo: float = -12.0, hi: float = 12.0) -> float:
    """E[max of k iid N(0,1)] = integral of x * k * phi(x) * Phi(x)^(k-1) dx, with Phi accumulated
    by the trapezoid rule on the same grid (no library normal CDF needed)."""
    phi = lambda x: math.exp(-x * x / 2) / math.sqrt(2 * math.pi)
    n = int(round((hi - lo) / h))
    Phi, s, p_prev, f_prev = 0.0, 0.0, phi(lo), 0.0
    for i in range(1, n + 1):
        x = lo + i * h
        p = phi(x)
        Phi = min(1.0, Phi + (p_prev + p) / 2 * h)
        f = x * k * p * Phi ** (k - 1)
        s += (f_prev + f) / 2 * h
        p_prev, f_prev = p, f
    return s


if __name__ == "__main__":
    for k in (2, 10, 30, 52):
        print(k, round(expected_max_normal(k), 4), round(math.sqrt(2 * math.log(k)), 4))
