# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from itertools import product

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from measurement.base import BidimensionalMeasure, MeasureBase

from . import utils


class MeasurementWidget(forms.MultiWidget):
    def __init__(self, attrs=None, float_widget=None,
                 unit_choices_widget=None, unit_choices=None, *args, **kwargs):

        self.unit_choices = unit_choices

        if not float_widget:
            float_widget = forms.TextInput(attrs=attrs)

        if not unit_choices_widget:
            unit_choices_widget = forms.Select(
                attrs=attrs,
                choices=unit_choices
            )

        widgets = (float_widget, unit_choices_widget)
        super(MeasurementWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            choice_units = set([
                u
                for u, n in self.unit_choices
            ])

            unit = value.STANDARD_UNIT
            if unit not in choice_units:
                unit = choice_units.pop()

            magnitude = getattr(value, unit)
            return [magnitude, unit]

        return [None, None]


class MeasurementField(forms.MultiValueField):
    def __init__(self, measurement, max_value=None, min_value=None,
                 unit_choices=None, validators=None, *args, **kwargs):

        if not issubclass(measurement, (MeasureBase, BidimensionalMeasure)):
            raise ValueError(
                "%s must be a subclass of MeasureBase" % measurement
            )

        self.measurement_class = measurement
        if not unit_choices:
            if issubclass(measurement, BidimensionalMeasure):
                unit_choices = tuple((
                    (
                        '{0}__{1}'.format(primary, reference),
                        '{0}__{1}'.format(primary, reference),
                    )
                    for primary, reference in product(
                        measurement.PRIMARY_DIMENSION.UNITS,
                        measurement.REFERENCE_DIMENSION.UNITS,
                    )
                ))
            else:
                unit_choices = tuple((
                    (u, u)
                    for u in measurement.UNITS
                ))

        if validators is None:
            validators = []

        if min_value is not None:
            if not isinstance(min_value, MeasureBase):
                msg = '"min_value" must be a measure, got %s' % type(min_value)
                raise ValueError(msg)
            validators += [MinValueValidator(min_value)]

        if max_value is not None:
            if not isinstance(max_value, MeasureBase):
                msg = '"max_value" must be a measure, got %s' % type(max_value)
                raise ValueError(msg)
            validators += [MaxValueValidator(max_value)]

        float_field = forms.FloatField(*args, **kwargs)
        choice_field = forms.ChoiceField(choices=unit_choices)
        defaults = {
            'widget': MeasurementWidget(
                float_widget=float_field.widget,
                unit_choices_widget=choice_field.widget,
                unit_choices=unit_choices
            ),
        }
        defaults.update(kwargs)
        fields = (float_field, choice_field)
        super(MeasurementField, self).__init__(fields, validators=validators,
                                               *args, **defaults)

    def compress(self, data_list):
        if not data_list:
            return None

        value, unit = data_list
        if value in self.empty_values:
            return None

        return utils.get_measurement(
            self.measurement_class,
            value,
            unit
        )
