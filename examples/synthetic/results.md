One noise seed per scene; GMM uses the stated K and EM starts. Results hold for these settings only.
Boundary recall/precision: share of true / predicted boundary pixels within 2 px of the other.
Label accuracy: each predicted group mapped to its majority true region (does not penalise extra groups).

| scene | method | groups / true | label accuracy | boundary recall | boundary precision |
| --- | --- | ---: | ---: | ---: | ---: |
| three_levels | GMM K=true components (no merging) | 3 / 3 | 0.999 | 1.000 | 1.000 |
| three_levels | GMM K=true groups | 3 / 3 | 0.999 | 1.000 | 1.000 |
| three_levels | GMM K=4 transitive groups | 3 / 3 | 0.997 | 1.000 | 0.961 |
| three_levels | GMM K=4 components (no merging) | 4 / 3 | 0.998 | 1.000 | 0.913 |
| three_levels | GMM K=4 groups | 3 / 3 | 0.997 | 1.000 | 0.961 |
| three_levels | histogram minima | 3 / 3 | 0.999 | 1.000 | 1.000 |
| three_levels | GMM K=4, 20 starts components (no merging) | 4 / 3 | 0.998 | 1.000 | 0.913 |
| three_levels | GMM K=4, 20 starts groups | 3 / 3 | 0.997 | 1.000 | 0.961 |
| three_levels | existing detector | — | — | 0.665 | 1.000 |
| close_levels | GMM K=true components (no merging) | 4 / 4 | 0.840 | 0.871 | 0.985 |
| close_levels | GMM K=true groups | 3 / 4 | 0.839 | 0.871 | 0.997 |
| close_levels | GMM K=4 transitive groups | 3 / 4 | 0.839 | 0.871 | 0.997 |
| close_levels | GMM K=4 components (no merging) | 4 / 4 | 0.840 | 0.871 | 0.985 |
| close_levels | GMM K=4 groups | 3 / 4 | 0.839 | 0.871 | 0.997 |
| close_levels | histogram minima | 3 / 4 | 0.840 | 0.871 | 1.000 |
| close_levels | GMM K=4, 20 starts components (no merging) | 4 / 4 | 0.840 | 0.871 | 0.985 |
| close_levels | GMM K=4, 20 starts groups | 3 / 4 | 0.839 | 0.871 | 0.997 |
| close_levels | existing detector | — | — | 0.760 | 1.000 |
| small_bright_spot | GMM K=true components (no merging) | 3 / 3 | 0.996 | 1.000 | 0.936 |
| small_bright_spot | GMM K=true groups | 2 / 3 | 0.994 | 1.000 | 0.967 |
| small_bright_spot | GMM K=4 transitive groups | 2 / 3 | 0.994 | 1.000 | 0.985 |
| small_bright_spot | GMM K=4 components (no merging) | 4 / 3 | 0.996 | 1.000 | 0.050 |
| small_bright_spot | GMM K=4 groups | 2 / 3 | 0.994 | 1.000 | 0.985 |
| small_bright_spot | histogram minima | 4 / 3 | 0.999 | 1.000 | 1.000 |
| small_bright_spot | GMM K=4, 20 starts components (no merging) | 4 / 3 | 0.998 | 1.000 | 0.968 |
| small_bright_spot | GMM K=4, 20 starts groups | 4 / 3 | 0.998 | 1.000 | 0.968 |
| small_bright_spot | existing detector | — | — | 0.896 | 1.000 |
| blurred_edges | GMM K=true components (no merging) | 3 / 3 | 0.976 | 1.000 | 0.553 |
| blurred_edges | GMM K=true groups | 2 / 3 | 0.936 | 0.900 | 0.811 |
| blurred_edges | GMM K=4 transitive groups | 3 / 3 | 0.982 | 0.949 | 0.639 |
| blurred_edges | GMM K=4 components (no merging) | 4 / 3 | 0.983 | 1.000 | 0.613 |
| blurred_edges | GMM K=4 groups | 3 / 3 | 0.982 | 0.949 | 0.639 |
| blurred_edges | histogram minima | 3 / 3 | 0.992 | 0.996 | 0.998 |
| blurred_edges | GMM K=4, 20 starts components (no merging) | 4 / 3 | 0.983 | 1.000 | 0.613 |
| blurred_edges | GMM K=4, 20 starts groups | 3 / 3 | 0.982 | 0.949 | 0.639 |
| blurred_edges | existing detector | — | — | 0.665 | 1.000 |
| illumination_ramp | GMM K=true components (no merging) | 2 / 2 | 0.998 | 1.000 | 0.715 |
| illumination_ramp | GMM K=true groups | 2 / 2 | 0.998 | 1.000 | 0.715 |
| illumination_ramp | GMM K=4 transitive groups | 4 / 2 | 0.999 | 1.000 | 0.067 |
| illumination_ramp | GMM K=4 components (no merging) | 4 / 2 | 0.999 | 1.000 | 0.067 |
| illumination_ramp | GMM K=4 groups | 4 / 2 | 0.999 | 1.000 | 0.067 |
| illumination_ramp | histogram minima | 3 / 2 | 0.999 | 1.000 | 0.146 |
| illumination_ramp | GMM K=4, 20 starts components (no merging) | 4 / 2 | 0.999 | 1.000 | 0.065 |
| illumination_ramp | GMM K=4, 20 starts groups | 4 / 2 | 0.999 | 1.000 | 0.065 |
| illumination_ramp | existing detector | — | — | 1.000 | 1.000 |
| noise_free | GMM K=true components (no merging) | 3 / 3 | 0.996 | 1.000 | 1.000 |
| noise_free | GMM K=true groups | 3 / 3 | 0.996 | 1.000 | 1.000 |
| noise_free | GMM K=4 transitive groups | 2 / 3 | 0.852 | 0.335 | 1.000 |
| noise_free | GMM K=4 components (no merging) | 4 / 3 | 0.997 | 1.000 | 1.000 |
| noise_free | GMM K=4 groups | 3 / 3 | 0.996 | 1.000 | 1.000 |
| noise_free | histogram minima | 6 / 3 | 0.999 | 1.000 | 1.000 |
| noise_free | GMM K=4, 20 starts components (no merging) | 4 / 3 | 0.997 | 1.000 | 1.000 |
| noise_free | GMM K=4, 20 starts groups | 3 / 3 | 0.996 | 1.000 | 1.000 |
| noise_free | existing detector | — | — | 0.665 | 1.000 |
