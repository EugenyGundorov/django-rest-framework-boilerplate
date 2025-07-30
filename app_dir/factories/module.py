import factory
from faker import Faker
from ..core.loading import get_model

faker  = Faker()


class ModuleFactory(factory.DjangoModelFactory):
    class Meta:
        model = get_model('module', 'Module')

    name = faker.name()
    description = faker.text()
