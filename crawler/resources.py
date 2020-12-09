from celery.utils.log import get_task_logger

from crawler.settings import (
    TENDER_HANDLERS,
    TENDER_OPT_FIELDS,
    CONTRACT_HANDLERS,
    CONTRACT_OPT_FIELDS,
    FRAMEWORK_HANDLERS,
    FRAMEWORK_OPT_FIELDS,
)
from environment_settings import (
    CRAWLER_TENDER_HANDLERS,
    CRAWLER_CONTRACT_HANDLERS,
    CRAWLER_FRAMEWORK_HANDLERS,
)

logger = get_task_logger(__name__)


class ResourceConfig:
    def __init__(self, handlers, opt_fields):
        """
        Feed resource config.
        :param handlers: list of feed handler functions
            handlers contains code that will be executed for every feed item
            these functions SHOULD NOT use database/API/any other IO calls
            handlers can add new tasks to the queue
            example: if(item["status"] == "awarding"){ attach_edr_yaml.delay(item["id"]) }
        :param opt_fields: list of feed extra field names
        """
        self.handlers = handlers
        self.opt_fields = opt_fields


class ResourceConfigBuilder:
    """
    Resource config builder
    """
    enabled_handlers_names = None
    handlers = ()
    opt_fields = ()

    def __init__(self):
        self.instance = None

    def __call__(self, resource, **kwargs):
        self.resource = resource
        if not self.instance:
            self.init_resource_config()
        return self.instance

    def init_resource_config(self):
        """
        Generates ResourceConfig instance
        :return: ResourceConfig instance
        """
        handlers_names = [i.__name__ for i in self.handlers]
        logger.info(f"Init {self.resource} handlers: {handlers_names}")
        self.instance = ResourceConfig(self.filter_handlers(), self.opt_fields)

    def filter_handlers(self):
        """
        Filters handlers with names provided in class enabled_handlers_names attribute
        :return: list of filtered feed handler functions
        """
        if self.enabled_handlers_names:
            logger.info(f"Filtering {self.resource} handlers with provided set: {self.enabled_handlers_names}")
            return [i for i in self.handlers if i.__name__ in self.enabled_handlers_names]
        return self.handlers


class TendersResourceConfigBuilder(ResourceConfigBuilder):
    handlers = TENDER_HANDLERS
    enabled_handlers_names = CRAWLER_TENDER_HANDLERS
    opt_fields = TENDER_OPT_FIELDS


class ContractsResourceConfigBuilder(ResourceConfigBuilder):
    handlers = CONTRACT_HANDLERS
    enabled_handlers_names = CRAWLER_CONTRACT_HANDLERS
    opt_fields = CONTRACT_OPT_FIELDS


class FrameworksResourceConfigBuilder(ResourceConfigBuilder):
    handlers = FRAMEWORK_HANDLERS
    enabled_handlers_names = CRAWLER_FRAMEWORK_HANDLERS
    opt_fields = FRAMEWORK_OPT_FIELDS


class ResourceConfigFactory:
    builders = None

    def __init__(self):
        self.builders = {}

    def register_builder(self, resource, builder):
        self.builders[resource] = builder

    def create(self, resource, **kwargs):
        builder = self.builders[resource]
        return builder(resource, **kwargs)


class ResourceConfigProvider(ResourceConfigFactory):
    def get(self, resource, **kwargs):
        return self.create(resource, **kwargs)


configs = ResourceConfigProvider()
configs.register_builder("tenders", TendersResourceConfigBuilder())
configs.register_builder("contracts", ContractsResourceConfigBuilder())
configs.register_builder("frameworks", FrameworksResourceConfigBuilder())
