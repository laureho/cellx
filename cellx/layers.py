from typing import List, Optional, Union

import tensorflow as tf
from tensorflow import keras as K


class ConvBlockBase(K.layers.Layer):
    """Base class for convolutional blocks.

    Keras layer to perform a convolution with batch normalization followed
    by activation.

    Parameters
    ----------
    convolution : keras.layers.Conv
        A convolutional layer for 2 or 3-dimensions.
    filters : int
        The number of convolutional filters.
    kernel_size : int, tuple
        Size of the convolutional kernel.
    padding : str
        Padding type for convolution.
    activation : str
        Name of activation function.
    strides : int
        Stride of the convolution.
    """

    def __init__(
        self,
        convolution: K.layers.Layer = K.layers.Conv2D,
        filters: int = 32,
        kernel_size: Union[int, tuple] = 3,
        padding: str = "same",
        strides: int = 1,
        activation: str = "swish",
        name: str = "ConvBlock",
        **kwargs
    ):
        super().__init__(name=name)

        self.conv = convolution(
            filters, kernel_size, strides=strides, padding=padding, **kwargs,
        )
        self.norm = K.layers.BatchNormalization()
        self.activation = K.layers.Activation(activation)

        # store the config so that we can restore it later
        self._config = {
            "filters": filters,
            "kernel_size": kernel_size,
            "padding": padding,
            "strides": strides,
            "activation": activation,
        }
        self._config.update(kwargs)

    def call(self, x, training: Optional[bool] = None):
        """Return the result of the normalized convolution."""
        conv = self.conv(x)
        conv = self.norm(conv, training=training)
        return self.activation(conv)

    def get_config(self) -> dict:
        config = super().get_config()
        config.update(self._config)
        return config


class ConvBlock2D(ConvBlockBase):
    """ConvBlock2D."""

    def __init__(self, **kwargs):
        super().__init__(convolution=K.layers.Conv2D, name="ConvBlock2D", **kwargs)


class ConvBlock3D(ConvBlockBase):
    """ConvBlock3D."""

    def __init__(self, **kwargs):
        super().__init__(convolution=K.layers.Conv3D, name="ConvBlock3D", **kwargs)


class EncoderDecoderBase(K.layers.Layer):
    """Base class for encoders and decoders.

    Parameters
    ----------
    convolution : ConvBlockBase
        A convolutional block layer.
    sampling : K.layers.Layer, None
        If not using pooling or upscaling, the stride of the convolution can be
        used instead.
    layers : list
        A list of kernels for each layer.

    Notes
    -----
    The list of kernels can be used to infer the number of conv-pool layers
    in the encoder.

    The type of sampling (pooling, transpose convolution or stride) and the
    order (before or after convoluton) varies between the derived Encoder and
    Decoder classes.
    """

    def __init__(
        self,
        convolution: ConvBlockBase = ConvBlock2D,
        sampling: Optional[K.layers.Layer] = K.layers.MaxPooling2D,
        layers: List[int] = [8, 16, 32],
        name: str = "EncoderDecoderBase",
        **kwargs
    ):
        super().__init__(name=name, **kwargs)

        if sampling is not None:
            if not isinstance(sampling, K.layers.Layer):
                self.sampling = sampling()
            else:
                self.sampling = sampling
            strides = 1
        else:
            self.sampling = lambda x: x
            strides = 2

        # build the convolutional layer list
        self.layers = [convolution(strides=strides) for k in layers]

        self._config = {
            "sampling": self.sampling,
            "layers": layers,
        }
        self._config.update(kwargs)

    def call(self, x, training: Optional[bool] = None):
        raise NotImplementedError

    def get_config(self) -> dict:
        config = super().get_config()
        config.update(self._config)
        return config


class Encoder2D(EncoderDecoderBase):
    """Encoder2D."""

    def __init__(
        self, convolution=ConvBlock2D, sampling=K.layers.MaxPooling2D, **kwargs
    ):
        super().__init__(
            convolution=convolution, sampling=sampling, name="Encoder2D", **kwargs
        )

    def call(self, x, training: Optional[bool] = None):
        for layer in self.layers:
            x = layer(x, training=training)
            x = self.sampling(x)
        return x


class Encoder3D(EncoderDecoderBase):
    """Encoder3D."""

    def __init__(
        self, convolution=ConvBlock3D, sampling=K.layers.MaxPooling3D, **kwargs
    ):
        super().__init__(
            convolution=convolution, sampling=sampling, name="Encoder3D", **kwargs
        )

    def call(self, x, training: Optional[bool] = None):
        for layer in self.layers:
            x = layer(x, training=training)
            x = self.sampling(x)
        return x


class Decoder2D(EncoderDecoderBase):
    """Decoder2D."""

    def __init__(
        self, convolution=ConvBlock2D, sampling=K.layers.UpSampling2D, **kwargs
    ):
        super().__init__(
            convolution=convolution, sampling=sampling, name="Decoder2D", **kwargs
        )

    def call(self, x, training: Optional[bool] = None):
        for layer in self.layers:
            x = self.sampling(x)
            x = layer(x, training=training)
        return x


class Decoder3D(EncoderDecoderBase):
    """Decoder3D."""

    def __init__(
        self, convolution=ConvBlock3D, sampling=K.layers.UpSampling3D, **kwargs
    ):
        super().__init__(
            convolution=convolution, sampling=sampling, name="Decoder3D", **kwargs
        )

    def call(self, x, training: Optional[bool] = None):
        for layer in self.layers:
            x = self.sampling(x)
            x = layer(x, training=training)
        return x


class Sampling(K.layers.Layer):
    """Uses (z_mean, z_log_var) to sample z."""

    def call(self, inputs):
        z_mean, z_log_var = inputs
        epsilon = K.backend.random_normal(shape=tf.shape(z_mean))
        return z_mean + tf.exp(0.5 * z_log_var) * epsilon


if __name__ == "__main__":
    # boilerplate
    pass
