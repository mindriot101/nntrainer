import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten

from .trainingoptions import TrainingOptions
from .architectures import ARCHITECTURES


class TrainerError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class ModelTrainer(object):
    def __init__(self, opts: TrainingOptions):
        self.opts = opts

    def run(self):
        model = self.build_model()

        training_datagen = self.build_datagen(self.opts.training_dir)
        if self.opts.validation_dir:
            validation_datagen = self.build_datagen(self.opts.validation_dir)
        else:
            validation_datagen = None

    def build_model(self):
        # Create the custom first layer, which has the dimensions of the data
        input_shape = (self.opts.image_shape[0], self.opts.image_shape[1], 3)
        input_tensor = tf.keras.layers.Input(shape=input_shape)

        # This is the base model class from the architecture that the user specified. We
        # constrain the solution to pre-trained models using imagenet weights.
        base_model = self.model_cls(
            weights="imagenet",
            include_top=False,
            input_tensor=input_tensor,
            classes=self.opts.output_classes,
        )

        # The final model
        model = Sequential()

        # Add the base model, i.e. the model that has already been trained using
        # ImageNet, minus the first few layers (as we asked for `include_top=False`).
        model.add(base_model)

        # Flatten the output of the feature extractor before adding the fully connected
        # layers.
        model.add(Flatten())

        # Add the fully connected layers
        for layer_idx in range(self.opts.num_fc_layers):
            model.add(Dense(self.opts.fc_neurones, activation="relu"))

        # Add the final classification layer
        model.add(Dense(self.opts.output_classes, activation="softmax"))

        # The model is complete, so compile it using the optimiser and loss functions
        # specified
        model.compile(
            optimizer=self.opts.optimiser,
            metrics=["accuracy"],
            loss=self.opts.loss_function,
        )

        return model

    def build_datagen(self, validation=False):
        if validation:
            gen = tf.keras.preprocessing.image.ImageDataGenerator(
                preprocessing_function=self.preprocess_input_fn()
            )
        else:
            gen = tf.keras.preprocessing.image.ImageDataGenerator(
                preprocessing_function=self.preprocess_input_fn(),
                horizontal_flip=self.opts.horizontal_flip,
                vertical_flip=self.opts.vertical_flip,
                rotation_range=self.opts.rotation_angle,
            )

        return gen

    def build_dataflow(self, datagen, validation=False):
        if validation:
            if self.opts.validation_dir is None:
                raise TrainerError("validation directory not set")
            return datagen.flow_from_directory(
                self.opts.validation_dir,
                target_size=self.opts.image_shape,
                batch_size=self.opts.batch_size,
            )
        else:
            if self.opts.training_dir is None:
                raise TrainerError("training directory not set")
            return datagen.flow_from_directory(
                self.opts.training_dir,
                target_size=self.opts.image_shape,
                batch_size=self.opts.batch_size,
            )

    def preprocess_input_fn(self):
        """Returns the correct function for preprocessing the data, based on the
        architecture that has been selected
        """
        fns = {
            tf.keras.applications.ResNet50: tf.keras.applications.resnet50.preprocess_input,
            tf.keras.applications.VGG16: tf.keras.applications.vgg16.preprocess_input,
        }

        return fns[self.model_cls]

    @property
    def model_cls(self):
        return ARCHITECTURES[self.opts.architecture]