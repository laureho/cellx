import numpy as np
from scipy.stats import binned_statistic_2d
from skimage.io import imread
from skimage.transform import resize
from tqdm import tqdm


def _load_and_normalize(filename: str, output_shape: tuple = (64, 64)):
    """Load an image, reshape to output_shape and normalize."""

    # reshape to a certain image size
    image = resize(imread(filename), output_shape, preserve_range=True)
    n_pixels = np.prod(output_shape)
    n_channels = image.shape[-1]

    a_std = lambda d: np.max([np.std(d), 1.0 / np.sqrt(n_pixels)])
    nrm = lambda d: np.clip((d - np.mean(d)) / a_std(d), -4.0, 4.0)

    for dim in range(n_channels):
        image[..., dim] = nrm(image[..., dim])

    # TODO(arl): ????
    image = np.clip(255.0 * ((image + 1.0) / 5.0), 0, 255)
    return image


class ManifoldProjection2D:
    """ManifoldProjection2D.

    Make a montage of image patches that represent examples from a manifold
    projection.

    Parameters
    ----------
    images : list of str or (N, W, H, C) np.ndarray
        A list of image filenames or a numpy array of N images, width W, height
        H, and C channels.
    output_shape : tuple of int
        Final size to reshape individual image patches to for the montage.
    preload_images : bool
        Preload images if a list of image filenames is provided, or not.
    """

    def __init__(
        self, images: list, output_shape: tuple = (64, 64), preload_images: bool = True,
    ):

        self._output_shape = output_shape
        self._images = None

        # check if `images` parameter is a list of strings or a numpy array
        # to preload images, or not
        if all([isinstance(img, str) for img in images]):
            if preload_images:
                self._images = [self._get_image(file) for file in tqdm(images)]
        else:
            if not isinstance(images, np.ndarray):
                raise ValueError("Image type unknown.")
            self._images = images

    def _get_image(self, filename: str) -> np.ndarray:
        """Grab an image and resize it."""
        return _load_and_normalize(filename, output_shape=self._output_shape)

    def __call__(
        self, manifold: np.ndarray, bins: int = 32, components: tuple = (0, 1)
    ) -> tuple:
        """Build the projection.

        Parameters
        ----------
        manifold : np.ndarray
            Numpy array of the manifold projection.
        bins : int
            Number of two-dimensional bins to group the manifold examples in.
        components : tuple of int
            Dimensions of manifold to use when creating the projection.

        Returns
        -------
        imgrid : np.ndarray
            An image with example image patches from the manifold arranged on a
            grid.
        extent : tuple
            Delimits the minimum and maximum bin edges, in each dimension, used
            to create the result.
        """

        assert manifold.shape[0] == len(self._images)

        # bin the manifold
        s, xe, ye, bn = binned_statistic_2d(
            manifold[:, components[0]],
            manifold[:, components[1]],
            [],
            bins=bins,
            statistic="count",
            expand_binnumbers=True,
        )

        bxy = zip(bn[0, :].tolist(), bn[1, :].tolist())

        # make a lookup dictionary
        grid = {}
        for idx, b in enumerate(bxy):
            if b not in grid:
                grid[b] = []

            if self._images is not None:
                grid[b].append(self._images[idx])
            else:
                if not grid[b]:
                    grid[b].append(self._get_image(self._image_files[idx]))

        # now make the grid image
        full_bins = [int(b) for b in self._output_shape]
        half_bins = [b // 2 for b in self._output_shape]
        imgrid = np.zeros(
            (
                (full_bins[0] + 1) * bins + half_bins[0],
                (full_bins[1] + 1) * bins + half_bins[1],
                3,
            ),
            dtype="uint8",
        )

        # build it
        for xy, images in tqdm(grid.items()):

            stack = np.stack(images, axis=0)
            im = np.mean(stack, axis=0)

            xx, yy = xy
            blockx = slice(
                xx * full_bins[0] - half_bins[0],
                (xx + 1) * full_bins[0] - half_bins[0],
                1,
            )
            blocky = slice(
                yy * full_bins[1] - half_bins[1],
                (yy + 1) * full_bins[1] - half_bins[1],
                1,
            )

            imgrid[blockx, blocky, :] = im

        extent = (min(xe), max(xe), min(ye), max(ye))

        return imgrid, extent


if __name__ == "__main__":
    pass
