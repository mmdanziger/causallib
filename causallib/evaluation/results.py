"""Evaluation results objects for plotting and further analysis.

These objects are generated by the `evaluate` method.
"""

import abc
import dataclasses
import inspect
from typing import Dict, List, Tuple, Union

import pandas as pd

from ..estimation.base_estimator import IndividualOutcomeEstimator
from ..estimation.base_weight import PropensityEstimator, WeightEstimator

from .predictions import WeightEvaluatorScores, SingleFoldPrediction
from .plots import mixins, data_extractors



@dataclasses.dataclass
class EvaluationResults(abc.ABC):
    """Data structure to hold evaluation results including cross-validation.

    Attrs:
        evaluated_metrics (pd.DataFrame or WeightEvaluatorScores):
        models (dict[str, Union[list[WeightEstimator], list[IndividualOutcomeEstimator]):
            Models trained during evaluation. May be dict or list or a model
            directly.
        predictions (dict[str, List[SingleFoldPredictions]]): dict with keys
            "train" and "valid" (if produced through cross-validation) and
            values of the predictions for the respective fold
        cv (list[tuple[list[int], list[int]]]): the cross validation indices,
            used to generate the results, used for constructing plots correctly
        X (pd.DataFrame): features data
        a (pd.Series): treatment assignment data
        y (pd.Series): outcome data
    """

    evaluated_metrics: Union[pd.DataFrame, WeightEvaluatorScores]
    models: Union[
        List[WeightEstimator],
        List[IndividualOutcomeEstimator],
        List[PropensityEstimator],
    ]
    predictions: Dict[str, List[SingleFoldPrediction]]
    cv: List[Tuple[List[int], List[int]]]
    X: pd.DataFrame
    a: pd.Series
    y: pd.Series

    @property
    def extractor(self):
        """Plot-data extractor for these results.

        Implemented by child classes.
        """
        raise NotImplementedError

    @staticmethod
    def make(
        evaluated_metrics: Union[pd.DataFrame, WeightEvaluatorScores],
        models: Union[
            List[WeightEstimator],
            List[IndividualOutcomeEstimator],
            List[PropensityEstimator],
        ],
        predictions: Dict[str, List[SingleFoldPrediction]],
        cv: List[Tuple[List[int], List[int]]],
        X: pd.DataFrame,
        a: pd.Series,
        y: pd.Series,
    ):
        if isinstance(models, dict):
            fitted_model = models["train"][0]
        elif isinstance(models, list):
            fitted_model = models[0]
        else:
            fitted_model = models

        if isinstance(fitted_model, PropensityEstimator):
            return PropensityEvaluationResults(
                evaluated_metrics, models, predictions, cv, X, a, y
            )
        if isinstance(fitted_model, WeightEstimator):
            return WeightEvaluationResults(
                evaluated_metrics, models, predictions, cv, X, a, y
            )
        if isinstance(fitted_model, IndividualOutcomeEstimator):
            if any(
                x and any(y.is_binary_outcome for y in x) for x in predictions.values()
            ):
                return BinaryOutcomeEvaluationResults(
                    evaluated_metrics, models, predictions, cv, X, a, y
                )
            return ContinuousOutcomeEvaluationResults(
                evaluated_metrics, models, predictions, cv, X, a, y
            )
        raise ValueError(
            f"Unable to find suitable results object for esimator of type {type(fitted_model)}"
        )

    @property
    def all_plot_names(self):
        """Available plot names.

        Returns:
            set[str]: string names of supported plot names for these results
        """
        return self.extractor.plot_names

    def get_data_for_plot(self, plot_name, phase="train"):
        """Get data for a given plot

        Args:
            plot_name (str): plot name from `self.all_plot_names`
            phase (str, optional): phase of interest. Defaults to "train".

        Returns:
            Any: the data required for the plot in question
        """
        return self.extractor.get_data_for_plot(plot_name, phase)


class WeightEvaluationResults(
    EvaluationResults,
    mixins.WeightPlotterMixin,
    mixins.PlotAllMixin,
):
    __doc__ = inspect.getdoc(EvaluationResults)

    @property
    def extractor(self):
        return data_extractors.WeightPlotDataExtractor(self)


class BinaryOutcomeEvaluationResults(
    EvaluationResults,
    mixins.ClassificationPlotterMixin,
    mixins.PlotAllMixin,
):
    __doc__ = inspect.getdoc(EvaluationResults)

    @property
    def extractor(self):
        return data_extractors.BinaryOutcomePlotDataExtractor(self)


class ContinuousOutcomeEvaluationResults(
    EvaluationResults,
    mixins.ContinuousOutcomePlotterMixin,
    mixins.PlotAllMixin,
):
    __doc__ = inspect.getdoc(EvaluationResults)

    @property
    def extractor(self):
        return data_extractors.ContinuousOutcomePlotDataExtractor(self)


class PropensityEvaluationResults(
    EvaluationResults,
    mixins.ClassificationPlotterMixin,
    mixins.WeightPlotterMixin,
    mixins.PlotAllMixin,
):
    __doc__ = inspect.getdoc(EvaluationResults)

    @property
    def extractor(self):
        return data_extractors.PropensityPlotDataExtractor(self)
