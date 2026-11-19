import numpy as np
from scipy.stats import chi2, binom

LAM = 0.94

def q(z, p):
    z = np.sort(z); n = len(z); h = (n - 1) * p; k = int(np.floor(h)); w = h - k
    return z[k] if k + 1 >= n else z[k] + w * (z[k + 1] - z[k])

C = np.array([100, 101, 99, 100, 97, 98, 99, 96, 93.0]); x = 10 * np.diff(C); W = 2
s2 = {W + 1: np.mean(x[:W] ** 2)}
for s in range(W + 1, 9):
    s2[s + 1] = LAM * s2[s] + (1 - LAM) * x[s - 1] ** 2
z = np.array([x[s - 1] / np.sqrt(s2[s]) for s in range(3, 8)])
Q = q(z, 0.01)
print("V1 sigma2:", [round(s2[s], 6) for s in range(3, 9)])
print("V1 sigma:", [round(np.sqrt(s2[s]), 6) for s in range(3, 9)])
print("V1 z:", z.round(6), "Q:", round(Q, 6), "VaR8:", round(-np.sqrt(s2[8]) * Q, 4))

T, p = 250, 0.01
xlogy = lambda a, b: 0.0 if a == 0 else a * np.log(b)
for b in [0, 1, 2, 3, 4, 5, 6, 7, 10]:
    LR = -2 * ((T - b) * np.log(1 - p) + xlogy(b, p) - xlogy(T - b, 1 - b / T) - xlogy(b, b / T))
    print(f"V5 x={b:2d} LR={LR:8.4f} p={1 - chi2.cdf(LR, 1):.4f}")
print("P(X>=5), binomial 1.3904%:", round(1 - binom.cdf(4, 250, 0.013904), 4))

def run(gen, seed, M=400, W=100, n=250, B=250):
    rng = np.random.default_rng(seed); counts = []
    for _ in range(M):
        N = W + n + B; e = rng.standard_normal(N); xs = e.copy(); sg = np.ones(N)
        v = np.mean(e[:W] ** 2)
        for s in range(W, N):
            sg[s] = np.sqrt(v)
            if gen == "ewma":
                xs[s] = sg[s] * e[s]
            v = LAM * v + (1 - LAM) * xs[s] ** 2
        zz = xs / sg
        counts.append(sum(zz[t] < q(zz[t - n:t], 0.01) for t in range(W + n, N)))
    c = np.array(counts)
    return c.mean() / B * 100, c.std(ddof=1) / np.sqrt(M) / B * 100, (c >= 5).mean()

for gen in ["ewma", "iid"]:
    for seed in [1, 2, 3, 4, 5]:
        rate, se, yellow = run(gen, seed)
        print(f"V2 {gen} seed={seed} rate={rate:.3f}% se={se:.3f}pp P(count>=5)={yellow:.3f}")
