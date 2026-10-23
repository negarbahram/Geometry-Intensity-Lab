Medians over distinct images (camera folders that reuse the same file are counted once).
detector matched = share of rasterised detector edge pixels with a region boundary within 3 px;
near detector = share of region boundary pixels within 3 px of a detector edge.

| dataset | group | variant | images | groups GMM / minima | boundary share of image GMM / minima | detector matched GMM / minima | near detector GMM / minima |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| isaacsim-images | 2592x1942 | cleanup | 22 | 2 / 1 | 0.8 % / 0.0 % | 6.1 % / 0.0 % | 0.2 % / 49.0 % |
| isaacsim-images | 2592x1942 | default | 22 | 2 / 1.5 | 0.8 % / 0.4 % | 14.9 % / 0.0 % | 0.4 % / 42.9 % |
| product-images | 1000x550 | cleanup | 10 | 3 / 4.5 | 1.0 % / 1.2 % | 42.5 % / 63.6 % | 14.1 % / 16.4 % |
| product-images | 1000x550 | default | 10 | 3 / 4 | 1.5 % / 1.7 % | 60.1 % / 77.4 % | 13.3 % / 14.6 % |
| product-images | 1200x670 | cleanup | 9 | 3 / 5 | 0.5 % / 2.1 % | 43.1 % / 87.6 % | 39.0 % / 26.1 % |
| product-images | 1200x670 | default | 9 | 3 / 4 | 1.6 % / 2.6 % | 52.1 % / 83.0 % | 12.5 % / 20.3 % |
| product-images | 6144x550 | cleanup | 18 | 4 / 8 | 1.0 % / 1.6 % | 65.5 % / 77.8 % | 4.5 % / 2.0 % |
| product-images | 6144x550 | default | 18 | 4 / 6 | 1.9 % / 2.3 % | 73.5 % / 82.2 % | 3.1 % / 1.8 % |
| product-images | 990x550 | cleanup | 16 | 3 / 4.5 | 1.2 % / 1.7 % | 50.2 % / 70.2 % | 13.4 % / 11.2 % |
| product-images | 990x550 | default | 16 | 3 / 4 | 2.1 % / 2.1 % | 54.0 % / 76.4 % | 10.3 % / 9.2 % |
