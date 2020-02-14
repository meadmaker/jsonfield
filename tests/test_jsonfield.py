from collections import OrderedDict
from decimal import Decimal

import django
from django.core.serializers import deserialize, serialize
from django.core.serializers.base import DeserializationError
from django.forms import ModelForm, ValidationError
from django.test import TestCase

from .models import (
    GenericForeignKeyObj,
    JSONCharModel,
    JSONModel,
    JSONModelCustomEncoders,
    JSONModelWithForeignKey,
    JSONNotRequiredModel,
    OrderedJSONModel,
    RemoteJSONModel,
)


class JSONModelWithForeignKeyTestCase(TestCase):
    def test_object_create(self):
        foreign_obj = GenericForeignKeyObj.objects.create(name='Brain')
        JSONModelWithForeignKey.objects.create(foreign_obj=foreign_obj)


class RemoteJSONFieldTests(TestCase):
    """Test JSON fields across a ForeignKey"""

    @classmethod
    def setUpTestData(cls):
        RemoteJSONModel.objects.create()

    def test_related_accessor(self):
        RemoteJSONModel.objects.get().foreign

    def test_select_related(self):
        RemoteJSONModel.objects.select_related('foreign').get()


class JSONFieldTest(TestCase):
    """JSONField Wrapper Tests"""

    json_model = JSONModel

    def test_json_field_create(self):
        """Test saving a JSON object in our JSONField"""
        json_obj = {
            "item_1": "this is a json blah",
            "blergh": "hey, hey, hey"}

        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_string_in_json_field(self):
        """Test saving an ordinary Python string in our JSONField"""
        json_obj = 'blah blah'
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_float_in_json_field(self):
        """Test saving a Python float in our JSONField"""
        json_obj = 1.23
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_int_in_json_field(self):
        """Test saving a Python integer in our JSONField"""
        json_obj = 1234567
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_decimal_in_json_field(self):
        """Test saving a Python Decimal in our JSONField"""
        json_obj = Decimal(12.34)
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        # here we must know to convert the returned string back to Decimal,
        # since json does not support that format
        self.assertEqual(Decimal(new_obj.json), json_obj)

    def test_json_field_modify(self):
        """Test modifying a JSON object in our JSONField"""
        json_obj_1 = {'a': 1, 'b': 2}
        json_obj_2 = {'a': 3, 'b': 4}

        obj = self.json_model.objects.create(json=json_obj_1)
        self.assertEqual(obj.json, json_obj_1)
        obj.json = json_obj_2

        self.assertEqual(obj.json, json_obj_2)
        obj.save()
        self.assertEqual(obj.json, json_obj_2)

        self.assertTrue(obj)

    def test_json_field_load(self):
        """Test loading a JSON object from the DB"""
        json_obj_1 = {'a': 1, 'b': 2}
        obj = self.json_model.objects.create(json=json_obj_1)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj_1)

    def test_json_list(self):
        """Test storing a JSON list"""
        json_obj = ["my", "list", "of", 1, "objs", {"hello": "there"}]

        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)
        self.assertEqual(new_obj.json, json_obj)

    def test_empty_objects(self):
        """Test storing empty objects"""
        for json_obj in [{}, [], 0, '', False]:
            obj = self.json_model.objects.create(json=json_obj)
            new_obj = self.json_model.objects.get(id=obj.id)
            self.assertEqual(json_obj, obj.json)
            self.assertEqual(json_obj, new_obj.json)

    def test_custom_encoder(self):
        """Test encoder_cls and object_hook"""
        value = 1 + 3j  # A complex number

        obj = JSONModelCustomEncoders.objects.create(json=value)
        new_obj = JSONModelCustomEncoders.objects.get(pk=obj.pk)
        self.assertEqual(value, new_obj.json)

    def test_django_serializers(self):
        """Test serializing/deserializing jsonfield data"""
        for json_obj in [{}, [], 0, '', False, {'key': 'value', 'num': 42,
                                                'ary': list(range(5)),
                                                'dict': {'k': 'v'}}]:
            obj = self.json_model.objects.create(json=json_obj)
            new_obj = self.json_model.objects.get(id=obj.id)
            self.assertTrue(new_obj)

        queryset = self.json_model.objects.all()
        ser = serialize('json', queryset)
        for dobj in deserialize('json', ser):
            obj = dobj.object
            pulled = self.json_model.objects.get(id=obj.pk)
            self.assertEqual(obj.json, pulled.json)

    def test_default_parameters(self):
        """Test providing a default value to the model"""
        model = JSONModel()
        model.json = {"check": 12}
        self.assertEqual(model.json, {"check": 12})
        self.assertEqual(type(model.json), dict)

        self.assertEqual(model.default_json, {"check": 12})
        self.assertEqual(type(model.default_json), dict)

    def test_invalid_json(self):
        # invalid json data {] in the json and default_json fields
        ser = '[{"pk": 1, "model": "tests.jsoncharmodel", ' \
            '"fields": {"json": "{]", "default_json": "{]"}}]'
        with self.assertRaises(DeserializationError) as cm:
            next(deserialize('json', ser))
        # Django 2 does not reraise DeserializationError as another DeserializationError
        # Changed in: https://github.com/django/django/pull/7878
        if django.VERSION < (2, 0,):
            inner = cm.exception.__context__.__context__
        else:
            inner = cm.exception.__context__
        self.assertIsInstance(inner, ValidationError)
        self.assertEqual('Enter valid JSON.', inner.messages[0])

    def test_integer_in_string_in_json_field(self):
        """Test saving the Python string '123' in our JSONField"""
        json_obj = '123'
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_boolean_in_string_in_json_field(self):
        """Test saving the Python string 'true' in our JSONField"""
        json_obj = 'true'
        obj = self.json_model.objects.create(json=json_obj)
        new_obj = self.json_model.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_pass_by_reference_pollution(self):
        """Make sure the default parameter is copied rather than passed by reference"""
        model = JSONModel()
        model.default_json["check"] = 144
        model.complex_default_json[0]["checkcheck"] = 144
        self.assertEqual(model.default_json["check"], 144)
        self.assertEqual(model.complex_default_json[0]["checkcheck"], 144)

        # Make sure when we create a new model, it resets to the default value
        # and not to what we just set it to (it would be if it were passed by reference)
        model = JSONModel()
        self.assertEqual(model.default_json["check"], 12)
        self.assertEqual(model.complex_default_json[0]["checkcheck"], 1212)

    def test_normal_regex_filter(self):
        """Make sure JSON model can filter regex"""

        JSONModel.objects.create(json={"boom": "town"})
        JSONModel.objects.create(json={"move": "town"})
        JSONModel.objects.create(json={"save": "town"})

        self.assertEqual(JSONModel.objects.count(), 3)

        self.assertEqual(JSONModel.objects.filter(json__regex=r"boom").count(), 1)
        self.assertEqual(JSONModel.objects.filter(json__regex=r"town").count(), 3)

    def test_save_blank_object(self):
        """Test that JSON model can save a blank object as none"""

        model = JSONModel()
        self.assertEqual(model.empty_default, {})

        model.save()
        self.assertEqual(model.empty_default, {})

        model1 = JSONModel(empty_default={"hey": "now"})
        self.assertEqual(model1.empty_default, {"hey": "now"})

        model1.save()
        self.assertEqual(model1.empty_default, {"hey": "now"})

    def test_model_full_clean(self):
        instances = [
            JSONNotRequiredModel(),
            JSONModel(json={'a': 'b'}),
        ]

        for instance in instances:
            with self.subTest(instance=instance):
                instance.full_clean()
                instance.save()


class JSONCharFieldTest(JSONFieldTest):
    json_model = JSONCharModel


class OrderedDictSerializationTest(TestCase):
    def setUp(self):
        self.ordered_dict = OrderedDict([
            ('number', [1, 2, 3, 4]),
            ('notes', True),
            ('alpha', True),
            ('romeo', True),
            ('juliet', True),
            ('bravo', True),
        ])
        self.expected_key_order = ['number', 'notes', 'alpha', 'romeo', 'juliet', 'bravo']

        self.instance = OrderedJSONModel.objects.create(json=self.ordered_dict)

    def test_load_kwargs_hook(self):
        from_db = OrderedJSONModel.objects.get(id=self.instance.id)

        # OrderedJSONModel explicitly sets `object_pairs_hook` to `OrderedDict`
        self.assertEqual(list(self.instance.json), self.expected_key_order)
        self.assertEqual(list(from_db.json), self.expected_key_order)
        self.assertIsInstance(from_db.json, OrderedDict)


class JSONModelFormTest(TestCase):
    def setUp(self):
        class JSONNotRequiredForm(ModelForm):
            class Meta:
                model = JSONNotRequiredModel
                fields = '__all__'

        self.form_class = JSONNotRequiredForm

    def test_blank_form(self):
        form = self.form_class(data={'json': ''})
        self.assertFalse(form.has_changed())

    def test_form_with_data(self):
        form = self.form_class(data={'json': '{}'})
        self.assertTrue(form.has_changed())

    def test_form_save(self):
        form = self.form_class(data={'json': ''})
        form.save()

    def test_save_values(self):
        values = [
            # (type, form input, db value)
            ('object', '{"a": "b"}', {'a': 'b'}),
            ('array', '[1, 2]', [1, 2]),
            ('string', '"test"', 'test'),
            ('float', '1.2', 1.2),
            ('int', '1234', 1234),
            ('bool', 'true', True),
            ('null', 'null', None),
        ]

        for vtype, form_value, db_value in values:
            with self.subTest(type=vtype, input=form_value, db=db_value):
                form = self.form_class(data={'json': form_value})
                self.assertTrue(form.is_valid(), msg=form.errors)

                instance = form.save()
                self.assertEqual(instance.json, db_value)

    def test_render_values(self):
        values = [
            # (type, db value, form output)
            ('object', {'a': 'b'}, '{\n    "a": "b"\n}'),
            ('array', [1, 2], "[\n    1,\n    2\n]"),
            ('string', 'test', '"test"'),
            ('float', 1.2, '1.2'),
            ('int', 1234, '1234'),
            ('bool', True, 'true'),
            ('null', None, 'null'),
        ]

        for vtype, db_value, form_value in values:
            with self.subTest(type=vtype, db=db_value, output=form_value):
                instance = JSONNotRequiredModel.objects.create(json=db_value)

                form = self.form_class(instance=instance)
                self.assertEqual(form['json'].value(), form_value)

    def test_invalid_value(self):
        form = self.form_class(data={'json': 'foo'})

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {
            'json': ['"foo" value must be valid JSON.'],
        })
        self.assertEqual(form['json'].value(), 'foo')
