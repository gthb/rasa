import logging
from typing import Any, Optional, Text, Tuple, Union

from rasa.nlu import config
from rasa.nlu.components import ComponentBuilder
from rasa.nlu.config import RasaNLUModelConfig
from rasa.nlu.model import Interpreter, Trainer
from rasa.nlu.training_data import load_data
from rasa.nlu.training_data.loading import load_data_from_endpoint
from rasa.utils.endpoints import EndpointConfig

logger = logging.getLogger(__name__)


class TrainingException(Exception):
    """Exception wrapping lower level exceptions that may happen while training

      Attributes:
          failed_target_project -- name of the failed project
          message -- explanation of why the request is invalid
      """

    def __init__(self, failed_target_project=None, exception=None):
        self.failed_target_project = failed_target_project
        if exception:
            self.message = exception.args[0]

    def __str__(self):
        return self.message


def create_persistor(persistor: Optional[Text]):
    """Create a remote persistor to store the model if configured."""

    if persistor is not None:
        from rasa.nlu.persistor import get_persistor

        return get_persistor(persistor)
    else:
        return None


def do_train_in_worker(
    cfg: RasaNLUModelConfig,
    data: Text,
    path: Text,
    fixed_model_name: Optional[Text] = None,
    storage: Optional[Text] = None,
    component_builder: Optional[ComponentBuilder] = None,
) -> Text:
    """Loads the trainer and the data and runs the training in a worker."""

    try:
        _, _, persisted_path = train(
            cfg, data, path, fixed_model_name, storage, component_builder
        )
        return persisted_path
    except BaseException as e:
        logger.exception("Failed to train on data '{}'.".format(data))
        raise TrainingException(path, e)


def train(
    nlu_config: Union[Text, RasaNLUModelConfig],
    data: Text,
    path: Optional[Text] = None,
    fixed_model_name: Optional[Text] = None,
    storage: Optional[Text] = None,
    component_builder: Optional[ComponentBuilder] = None,
    training_data_endpoint: Optional[EndpointConfig] = None,
    **kwargs: Any
) -> Tuple[Trainer, Interpreter, Text]:
    """Loads the trainer and the data and runs the training of the model."""

    if isinstance(nlu_config, str):
        nlu_config = config.load(nlu_config)

    # Ensure we are training a model that we can save in the end
    # WARN: there is still a race condition if a model with the same name is
    # trained in another subprocess
    trainer = Trainer(nlu_config, component_builder)
    persistor = create_persistor(storage)
    if training_data_endpoint is not None:
        training_data = load_data_from_endpoint(
            training_data_endpoint, nlu_config.language
        )
    else:
        training_data = load_data(data, nlu_config.language)
    interpreter = trainer.train(training_data, **kwargs)

    if path:
        persisted_path = trainer.persist(path, persistor, fixed_model_name)
    else:
        persisted_path = None

    return trainer, interpreter, persisted_path


if __name__ == "__main__":
    raise RuntimeError(
        "Calling `rasa.nlu.train` directly is no longer supported. Please use "
        "`rasa train` to train a combined Core and NLU model or `rasa train nlu` "
        "to train an NLU model."
    )
