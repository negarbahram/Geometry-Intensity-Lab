Boundary recall/precision: share of true / predicted boundary pixels within 2 px of the other.
Label accuracy: each predicted group mapped to its majority true region (does not penalise extra groups).

| scene | method | groups / true | label accuracy | boundary recall | boundary precision |
| --- | --- | ---: | ---: | ---: | ---: |
| three_levels | GMM K=true | 3 / 3 | 0.999 | 1.000 | 1.000 |
| three_levels | GMM K=4 transitive | 3 / 3 | 0.997 | 1.000 | 0.961 |
| three_levels | GMM K=4 | 3 / 3 | 0.997 | 1.000 | 0.961 |
| three_levels | histogram minima | 3 / 3 | 0.999 | 1.000 | 1.000 |
| three_levels | existing detector | — | — | 0.665 | 1.000 |
| close_levels | GMM K=true | 3 / 4 | 0.839 | 0.871 | 0.997 |
| close_levels | GMM K=4 transitive | 3 / 4 | 0.839 | 0.871 | 0.997 |
| close_levels | GMM K=4 | 3 / 4 | 0.839 | 0.871 | 0.997 |
| close_levels | histogram minima | 3 / 4 | 0.840 | 0.871 | 1.000 |
| close_levels | existing detector | — | — | 0.760 | 1.000 |
| small_bright_spot | GMM K=true | 2 / 3 | 0.994 | 1.000 | 0.967 |
| small_bright_spot | GMM K=4 transitive | 2 / 3 | 0.994 | 1.000 | 0.985 |
| small_bright_spot | GMM K=4 | 2 / 3 | 0.994 | 1.000 | 0.985 |
| small_bright_spot | histogram minima | 4 / 3 | 0.999 | 1.000 | 1.000 |
| small_bright_spot | existing detector | — | — | 0.896 | 1.000 |
| blurred_edges | GMM K=true | 2 / 3 | 0.936 | 0.900 | 0.811 |
| blurred_edges | GMM K=4 transitive | 3 / 3 | 0.982 | 0.949 | 0.639 |
| blurred_edges | GMM K=4 | 3 / 3 | 0.982 | 0.949 | 0.639 |
| blurred_edges | histogram minima | 3 / 3 | 0.992 | 0.996 | 0.998 |
| blurred_edges | existing detector | — | — | 0.665 | 1.000 |
| illumination_ramp | GMM K=true | 2 / 2 | 0.998 | 1.000 | 0.715 |
| illumination_ramp | GMM K=4 transitive | 4 / 2 | 0.999 | 1.000 | 0.067 |
| illumination_ramp | GMM K=4 | 4 / 2 | 0.999 | 1.000 | 0.067 |
| illumination_ramp | histogram minima | 3 / 2 | 0.999 | 1.000 | 0.146 |
| illumination_ramp | existing detector | — | — | 1.000 | 1.000 |
| noise_free | GMM K=true | 3 / 3 | 0.996 | 1.000 | 1.000 |
| noise_free | GMM K=4 transitive | 2 / 3 | 0.852 | 0.335 | 1.000 |
| noise_free | GMM K=4 | 3 / 3 | 0.996 | 1.000 | 1.000 |
| noise_free | histogram minima | 6 / 3 | 0.999 | 1.000 | 1.000 |
| noise_free | existing detector | — | — | 0.665 | 1.000 |
