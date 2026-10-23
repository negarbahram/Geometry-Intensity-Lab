# Parity results: C++ port vs Python reference (a79e332)

Status `pass` = every comparison within the tolerances of cpp/PORTING_PLAN.md. With the default 5 EM starts the random starts differ by design (NumPy PCG64 vs std::mt19937_64): `pass (same optimum)` = a different start won but reached the same maximum (LL within 1e-7, parameters within 0.05); `pass (different optimum)` = the starts found different local maxima. In both cases the downstream outputs are reported, not required to match.

| case | variant | status | gray px diff | fit Δmean / Δσ | LL rel diff | EM iter Py/C++ | LUT diffs comp/grp/min | label px diff comp/grp/min | boundary px diff comp/grp/min | Python s | C++ s |
| --- | --- | --- | ---: | --- | ---: | --- | --- | --- | --- | ---: | ---: |
| synthetic/three_levels | default | pass (same optimum) | 0 | 0.01 / 0.0048 | 6.4e-10 | 233/318 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.433 | 0.188 |
| synthetic/three_levels | one_start | pass | 0 | 6.4e-14 / 1.4e-14 | 0.0e+00 | 54/54 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.083 | 0.08 |
| synthetic/three_levels | transitive | pass | 0 | 6.4e-14 / 1.4e-14 | 0.0e+00 | 54/54 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.083 | 0.08 |
| synthetic/three_levels | uncertain | pass | 0 | 6.4e-14 / 1.4e-14 | 0.0e+00 | 54/54 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.08 | 0.074 |
| synthetic/three_levels | cleanup | pass | 0 | 9.3e-12 / 2.2e-12 | 1.5e-16 | 1468/1468 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.483 | 0.119 |
| synthetic/close_levels | default | pass (same optimum) | 0 | 0.028 / 0.0063 | 1.5e-09 | 868/1598 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.292 | 0.217 |
| synthetic/close_levels | one_start | pass | 0 | 8.5e-14 / 5.3e-14 | 1.1e-16 | 760/760 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.273 | 0.104 |
| synthetic/close_levels | transitive | pass | 0 | 8.5e-14 / 5.3e-14 | 1.1e-16 | 760/760 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.262 | 0.104 |
| synthetic/close_levels | uncertain | pass | 0 | 8.5e-14 / 5.3e-14 | 1.1e-16 | 760/760 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.26 | 0.103 |
| synthetic/close_levels | cleanup | pass | 0 | 1.3e-13 / 5.7e-14 | 4.1e-16 | 2000/2000 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.547 | 0.117 |
| synthetic/small_bright_spot | default | pass (same optimum) | 0 | 0.013 / 0.0063 | 9.0e-08 | 24/62 | 2/0/0 | 3616 / 0 / 0 | 8553 / 0 / 0 | 1.171 | 0.176 |
| synthetic/small_bright_spot | one_start | pass | 0 | 1.5e-13 / 3.6e-14 | 3.9e-16 | 246/246 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.281 | 0.112 |
| synthetic/small_bright_spot | transitive | pass | 0 | 1.5e-13 / 3.6e-14 | 3.9e-16 | 246/246 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.28 | 0.111 |
| synthetic/small_bright_spot | uncertain | pass | 0 | 1.5e-13 / 3.6e-14 | 3.9e-16 | 246/246 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.338 | 0.108 |
| synthetic/small_bright_spot | cleanup | pass | 0 | 9.7e-12 / 5.5e-12 | 7.8e-16 | 2000/2000 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.491 | 0.121 |
| synthetic/blurred_edges | default | pass (same optimum) | 0 | 0.0025 / 0.0012 | 3.5e-10 | 753/115 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.785 | 0.311 |
| synthetic/blurred_edges | one_start | pass | 0 | 3.1e-13 / 5.7e-14 | 2.4e-16 | 58/58 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.186 | 0.101 |
| synthetic/blurred_edges | transitive | pass | 0 | 3.1e-13 / 5.7e-14 | 2.4e-16 | 58/58 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.184 | 0.1 |
| synthetic/blurred_edges | uncertain | pass | 0 | 3.1e-13 / 5.7e-14 | 2.4e-16 | 58/58 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.18 | 0.094 |
| synthetic/blurred_edges | cleanup | pass | 0 | 9.9e-14 / 4.1e-14 | 3.0e-16 | 521/521 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.206 | 0.087 |
| synthetic/illumination_ramp | default | pass (same optimum) | 0 | 0.0021 / 0.00054 | 4.5e-09 | 456/451 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.58 | 0.268 |
| synthetic/illumination_ramp | one_start | pass | 0 | 1.3e-13 / 1.4e-14 | 6.1e-16 | 415/415 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.306 | 0.108 |
| synthetic/illumination_ramp | transitive | pass | 0 | 1.3e-13 / 1.4e-14 | 6.1e-16 | 415/415 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.306 | 0.11 |
| synthetic/illumination_ramp | uncertain | pass | 0 | 1.3e-13 / 1.4e-14 | 6.1e-16 | 415/415 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.308 | 0.111 |
| synthetic/illumination_ramp | cleanup | pass | 0 | 2e-13 / 9.1e-14 | 4.2e-16 | 191/191 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.179 | 0.084 |
| synthetic/noise_free | default | pass (same optimum) | 0 | 2.2e-05 / 4.4e-06 | 1.8e-15 | 7/6 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.079 | 0.05 |
| synthetic/noise_free | one_start | pass | 0 | 2.8e-14 / 7.1e-15 | 0.0e+00 | 5/5 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.025 | 0.048 |
| synthetic/noise_free | transitive | pass | 0 | 2.8e-14 / 7.1e-15 | 0.0e+00 | 5/5 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.027 | 0.049 |
| synthetic/noise_free | uncertain | pass | 0 | 2.8e-14 / 7.1e-15 | 0.0e+00 | 5/5 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.025 | 0.048 |
| synthetic/noise_free | cleanup | pass | 0 | 7.1e-15 / 0 | 2.1e-16 | 6/6 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.038 | 0.052 |
| product/top/Good Parts/Good Parts10-15/Pic_2026_10_15_151035_21.bmp | default | pass | 0 | 8.5e-14 / 2.1e-14 | 7.5e-16 | 51/51 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.496 | 0.506 |
| product/top/Good Parts/Good Parts10-15/Pic_2026_10_15_151035_21.bmp | one_start | pass | 0 | 8.5e-14 / 2.1e-14 | 7.5e-16 | 51/51 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.492 | 0.237 |
| product/top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp | default | pass (different optimum) | 0 | 29 / 15 | 1.2e-04 | 30/150 | 38/0/0 | 90960 / 0 / 0 | 55429 / 0 / 0 | 1.988 | 0.471 |
| product/top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp | one_start | pass | 0 | 1.7e-13 / 5e-14 | 2.4e-15 | 377/377 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.573 | 0.234 |
| product/top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp | transitive | pass | 0 | 1.7e-13 / 5e-14 | 2.4e-15 | 377/377 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.585 | 0.243 |
| product/top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp | uncertain | pass | 0 | 1.7e-13 / 5e-14 | 2.4e-15 | 377/377 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.572 | 0.238 |
| product/top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp | cleanup | pass | 0 | 7.1e-14 / 1.4e-14 | 1.6e-15 | 213/213 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.461 | 0.215 |
| product/bottom/Good Parts/Good Parts10-8(2)/Pic_2026_10_08_115202_10.bmp | default | pass | 0 | 1.4e-13 / 2.8e-14 | 0.0e+00 | 78/78 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.764 | 0.398 |
| product/bottom/Good Parts/Good Parts10-8(2)/Pic_2026_10_08_115202_10.bmp | one_start | pass | 0 | 1.4e-13 / 2.8e-14 | 0.0e+00 | 78/78 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.461 | 0.224 |
| product/bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp | default | pass (same optimum) | 0 | 0.00086 / 0.00062 | 1.5e-09 | 139/76 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.313 | 0.35 |
| product/bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp | one_start | pass | 0 | 1.8e-13 / 1.6e-13 | 3.5e-16 | 403/403 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.299 | 0.19 |
| product/bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp | transitive | pass | 0 | 1.8e-13 / 1.6e-13 | 3.5e-16 | 403/403 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.302 | 0.199 |
| product/bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp | uncertain | pass | 0 | 1.8e-13 / 1.6e-13 | 3.5e-16 | 403/403 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.309 | 0.197 |
| product/bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp | cleanup | pass | 0 | 8.5e-14 / 5.7e-14 | 1.7e-16 | 252/252 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.503 | 0.238 |
| product/front/RHS_NG/RHS_NG-10-6(2)/Pic_2026_10_06_154528_2.bmp | default | pass (same optimum) | 0 | 0.0011 / 0.00037 | 3.4e-09 | 114/114 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.299 | 0.466 |
| product/front/RHS_NG/RHS_NG-10-6(2)/Pic_2026_10_06_154528_2.bmp | one_start | pass | 0 | 5e-14 / 2.1e-14 | 1.0e-15 | 114/114 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.424 | 0.278 |
| product/rear/Good Parts/Good Parts 10-6(1)/Pic_2026_10_06_125715_14.bmp | default | pass (same optimum) | 0 | 0.00089 / 0.00062 | 1.2e-09 | 64/80 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.98 | 0.777 |
| product/rear/Good Parts/Good Parts 10-6(1)/Pic_2026_10_06_125715_14.bmp | one_start | pass | 0 | 1.4e-14 / 0 | 1.5e-16 | 29/29 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.568 | 0.7 |
| isaac/top/isaacsim-samples/rgb_0143.png | default | pass (same optimum) | 0 | 0.0011 / 0.00028 | 8.5e-10 | 133/122 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.867 | 0.734 |
| isaac/top/isaacsim-samples/rgb_0143.png | one_start | pass | 0 | 5.7e-14 / 4.3e-14 | 1.6e-16 | 153/153 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.146 | 0.635 |
| isaac/top/isaacsim-samples/rgb_0143.png | transitive | pass | 0 | 5.7e-14 / 4.3e-14 | 1.6e-16 | 153/153 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.18 | 0.654 |
| isaac/top/isaacsim-samples/rgb_0143.png | uncertain | pass | 0 | 5.7e-14 / 4.3e-14 | 1.6e-16 | 153/153 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.202 | 0.693 |
| isaac/top/isaacsim-samples/rgb_0143.png | cleanup | pass | 0 | 8.5e-14 / 3.5e-14 | 3.1e-16 | 167/167 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.678 | 0.81 |
| isaac/top/isaacsim-samples/rgb_0317.png | default | pass | 0 | 1.4e-13 / 4.3e-14 | 1.6e-16 | 227/227 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.637 | 0.693 |
| isaac/top/isaacsim-samples/rgb_0317.png | one_start | pass | 0 | 1.4e-13 / 4.3e-14 | 1.6e-16 | 227/227 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.076 | 0.619 |
| isaac/front/isaacsim-samples/rgb_0046.png | default | pass (different optimum) | 0 | 17 / 2.9 | 6.3e-04 | 37/353 | 20/25/0 | 1503771 / 3552565 / 0 | 102444 / 21112 / 0 | 1.632 | 0.763 |
| isaac/front/isaacsim-samples/rgb_0046.png | one_start | pass | 0 | 8.5e-14 / 3.6e-14 | 1.3e-15 | 219/219 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.312 | 0.732 |
| isaac/front/isaacsim-samples/rgb_0046.png | transitive | pass | 0 | 8.5e-14 / 3.6e-14 | 1.3e-15 | 219/219 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.315 | 0.734 |
| isaac/front/isaacsim-samples/rgb_0046.png | uncertain | pass | 0 | 8.5e-14 / 3.6e-14 | 1.3e-15 | 219/219 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.391 | 0.776 |
| isaac/front/isaacsim-samples/rgb_0046.png | cleanup | pass | 0 | 1.3e-13 / 2.9e-14 | 0.0e+00 | 207/207 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 2.595 | 1.061 |
| isaac/front/isaacsim-samples/rgb_0137.png | default | pass (different optimum) | 0 | 19 / 29 | 2.6e-03 | 66/63 | 134/49/0 | 4146503 / 536268 / 0 | 65769 / 33012 / 0 | 1.624 | 0.785 |
| isaac/front/isaacsim-samples/rgb_0137.png | one_start | pass | 0 | 2e-13 / 6.6e-14 | 5.7e-16 | 269/269 | 0/0/0 | 0 / 0 / 0 | 0 / 0 / 0 | 1.318 | 0.742 |

## Issues (0)


## Notes (42)

* synthetic/three_levels [default]: same optimum: K=4 fit differs (means 0.0105, sigmas 0.00477, LL rel 6.40e-10, EM iterations 233/318); higher likelihood: Python; C++ winning start 1
* synthetic/three_levels [default]: K sweep: different fits at K = [5, 6, 7, 8]
* synthetic/three_levels [default]: downstream of the same optimum: separation max diff 0.001, groups equal, LUT values differing {'gmm_components': 0, 'gmm': 0, 'minima': 0}
* synthetic/close_levels [default]: same optimum: K=4 fit differs (means 0.0278, sigmas 0.00631, LL rel 1.51e-09, EM iterations 868/1598); higher likelihood: C++; C++ winning start 3
* synthetic/close_levels [default]: K sweep: different fits at K = [5, 6, 7, 8]
* synthetic/close_levels [default]: downstream of the same optimum: separation max diff 0.002, groups equal, LUT values differing {'gmm_components': 0, 'gmm': 0, 'minima': 0}
* synthetic/small_bright_spot [default]: same optimum: K=4 fit differs (means 0.0131, sigmas 0.00626, LL rel 9.04e-08, EM iterations 24/62); higher likelihood: C++; C++ winning start 2
* synthetic/small_bright_spot [default]: K sweep: different fits at K = [4, 5, 6, 7, 8]
* synthetic/small_bright_spot [default]: downstream of the same optimum: separation max diff 0.015, groups equal, LUT values differing {'gmm_components': 2, 'gmm': 0, 'minima': 0}
* synthetic/blurred_edges [default]: same optimum: K=4 fit differs (means 0.00248, sigmas 0.00115, LL rel 3.50e-10, EM iterations 753/115); higher likelihood: Python; C++ winning start 1
* synthetic/blurred_edges [default]: K sweep: different fits at K = [5, 6, 7, 8]
* synthetic/blurred_edges [default]: downstream of the same optimum: separation max diff 0, groups equal, LUT values differing {'gmm_components': 0, 'gmm': 0, 'minima': 0}
* synthetic/illumination_ramp [default]: same optimum: K=4 fit differs (means 0.00215, sigmas 0.000541, LL rel 4.47e-09, EM iterations 456/451); higher likelihood: Python; C++ winning start 3
* synthetic/illumination_ramp [default]: K sweep: different fits at K = [2, 6, 7, 8]
* synthetic/illumination_ramp [default]: downstream of the same optimum: separation max diff 0.001, groups equal, LUT values differing {'gmm_components': 0, 'gmm': 0, 'minima': 0}
* synthetic/noise_free [default]: same optimum: K=4 fit differs (means 2.24e-05, sigmas 4.42e-06, LL rel 1.83e-15, EM iterations 7/6); higher likelihood: C++; C++ winning start 1
* synthetic/noise_free [default]: K sweep: different fits at K = [3, 7, 8]
* synthetic/noise_free [default]: downstream of the same optimum: separation max diff 0, groups equal, LUT values differing {'gmm_components': 0, 'gmm': 0, 'minima': 0}
* product-images/top/Good Parts/Good Parts10-15/Pic_2026_10_15_151035_21.bmp [default]: K sweep: different fits at K = [3, 5, 7, 8]
* product-images/top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp [default]: different optimum: K=4 fit differs (means 29.1, sigmas 14.9, LL rel 1.21e-04, EM iterations 30/150); higher likelihood: Python; C++ winning start 3
* product-images/top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp [default]: K sweep: different fits at K = [4, 5, 6, 7, 8]
* product-images/top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp [default]: downstream of the different optimum: separation max diff 4.93, groups equal, LUT values differing {'gmm_components': 38, 'gmm': 0, 'minima': 0}
* product-images/bottom/Good Parts/Good Parts10-8(2)/Pic_2026_10_08_115202_10.bmp [default]: K sweep: different fits at K = [5, 6, 7, 8]
* product-images/bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp [default]: same optimum: K=4 fit differs (means 0.000857, sigmas 0.000622, LL rel 1.53e-09, EM iterations 139/76); higher likelihood: Python; C++ winning start 1
* product-images/bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp [default]: K sweep: different fits at K = [2, 5, 6, 7, 8]
* product-images/bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp [default]: downstream of the same optimum: separation max diff 0.009, groups equal, LUT values differing {'gmm_components': 0, 'gmm': 0, 'minima': 0}
* product-images/front/RHS_NG/RHS_NG-10-6(2)/Pic_2026_10_06_154528_2.bmp [default]: same optimum: K=4 fit differs (means 0.00111, sigmas 0.000367, LL rel 3.38e-09, EM iterations 114/114); higher likelihood: C++; C++ winning start 2
* product-images/front/RHS_NG/RHS_NG-10-6(2)/Pic_2026_10_06_154528_2.bmp [default]: K sweep: different fits at K = [5, 6, 7, 8]
* product-images/front/RHS_NG/RHS_NG-10-6(2)/Pic_2026_10_06_154528_2.bmp [default]: downstream of the same optimum: separation max diff 0.001, groups equal, LUT values differing {'gmm_components': 0, 'gmm': 0, 'minima': 0}
* product-images/rear/Good Parts/Good Parts 10-6(1)/Pic_2026_10_06_125715_14.bmp [default]: same optimum: K=4 fit differs (means 0.000889, sigmas 0.00062, LL rel 1.22e-09, EM iterations 64/80); higher likelihood: C++; C++ winning start 3
* product-images/rear/Good Parts/Good Parts 10-6(1)/Pic_2026_10_06_125715_14.bmp [default]: K sweep: different fits at K = [5, 6, 7, 8]
* product-images/rear/Good Parts/Good Parts 10-6(1)/Pic_2026_10_06_125715_14.bmp [default]: downstream of the same optimum: separation max diff 0.001, groups equal, LUT values differing {'gmm_components': 0, 'gmm': 0, 'minima': 0}
* isaacsim-images/top/isaacsim-samples/rgb_0143.png [default]: same optimum: K=4 fit differs (means 0.00112, sigmas 0.000278, LL rel 8.55e-10, EM iterations 133/122); higher likelihood: C++; C++ winning start 4
* isaacsim-images/top/isaacsim-samples/rgb_0143.png [default]: K sweep: different fits at K = [5, 7, 8]
* isaacsim-images/top/isaacsim-samples/rgb_0143.png [default]: downstream of the same optimum: separation max diff 0, groups equal, LUT values differing {'gmm_components': 0, 'gmm': 0, 'minima': 0}
* isaacsim-images/top/isaacsim-samples/rgb_0317.png [default]: K sweep: different fits at K = [6, 7, 8]
* isaacsim-images/front/isaacsim-samples/rgb_0046.png [default]: different optimum: K=4 fit differs (means 16.8, sigmas 2.9, LL rel 6.34e-04, EM iterations 37/353); higher likelihood: Python; C++ winning start 4
* isaacsim-images/front/isaacsim-samples/rgb_0046.png [default]: K sweep: different fits at K = [4, 5, 6]
* isaacsim-images/front/isaacsim-samples/rgb_0046.png [default]: downstream of the different optimum: separation max diff 6.83, groups differ, LUT values differing {'gmm_components': 20, 'gmm': 25, 'minima': 0}
* isaacsim-images/front/isaacsim-samples/rgb_0137.png [default]: different optimum: K=4 fit differs (means 19.3, sigmas 28.6, LL rel 2.57e-03, EM iterations 66/63); higher likelihood: C++; C++ winning start 1
* isaacsim-images/front/isaacsim-samples/rgb_0137.png [default]: K sweep: different fits at K = [4, 6]
* isaacsim-images/front/isaacsim-samples/rgb_0137.png [default]: downstream of the different optimum: separation max diff 27.2, groups differ, LUT values differing {'gmm_components': 134, 'gmm': 49, 'minima': 0}

Total time over 62 cases: Python 47.1 s (in-process, no detector), C++ 20.0 s (CLI including process start, PNG and JSON writing).
