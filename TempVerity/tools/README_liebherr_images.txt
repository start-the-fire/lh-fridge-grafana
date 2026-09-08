TempVerity Liebherr Image Fetcher – Hi-Res revision

This revision uses the structured product-image metadata embedded in Liebherr
product pages.

It prefers:
    assetType = product_image
    derivate = web
    native extension = JPG (where reported)

Example structure found on the HMFvh 4011 page:
    .../versions/<uuid>/web/HMFvh%204011.jpg

This is preferred over:
    .../w-1280_h-1280_f-webp/HMFvh%204011.webp
    .../thumbnail/HMFvh%204011.webp

For a useful TempVerity device card image, the selection preference is:
    straight_closed_empty
    oblique_closed_empty
    straight_open_empty
    oblique_open_empty
    ambient

If the structured metadata is unavailable, the downloader falls back to the
1280x1280 WebP derivative.

Run:
    python3 download_liebherr_images.py --output ../data/images/catalog

Download one missing model:
    python3 download_liebherr_images.py --only-model "HMFvh 4011" --output ../data/images/catalog

TempVerity checks this catalog after discovering a Liebherr model and serves the
matching local image. The downloader uses official images from liebherr.com.
