"""
(C) Copyright 2019 IBM Corp.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on Dec 25, 2018

"""

import numpy as np
import pandas as pd

from .predictor import Predictor
from ..estimation.base_weight import WeightEstimator, PropensityEstimator
from ..utils.stat_utils import robust_lookup
from .metrics import Scorer, calculate_covariate_balance, WeightEvaluatorScores
# TODO: decide what implementation stays - the one with the '2' suffix or the one without.
#       The one with is based on matrix input and does all the vector extraction by itself.
#       The one without is simpler one the receive the vectors already (more general, as not all models may have matrix.


# ################ #
# Weight Evaluator #
# ################ #

class WeightEvaluatorPredictions:
    """Data structure to hold weight-model predictions"""

    def __init__(self, weight_by_treatment_assignment, weight_for_being_treated, treatment_assignment_pred):
        self.weight_by_treatment_assignment = weight_by_treatment_assignment
        self.weight_for_being_treated = weight_for_being_treated
        self.treatment_assignment_pred = treatment_assignment_pred

    def calculate_metrics(self, X, a_true, metrics_to_evaluate):
        """
        TODO: fix these docs
        Args:
            X (pd.DataFrame): Covariates.
            targets (pd.Series): Target variable - true treatment assignment
            predict_scores (pd.Series): Continuous prediction of the treatment assignment
                                        (as is `predict_proba` or `decision_function`).
            predict_assignment (pd.Series): Class prediction of the treatment assignment
                                            (i.e. prediction of the assignment it self).
            predict_weights (pd.Series): The weights derived to balance between the treatment groups
                                         (here, called `targets`).
            metrics_to_evaluate (dict | None): key: metric's name, value: callable that receives true labels, prediction
                                               and sample_weights (the latter is allowed to be ignored).
                                               If not provided, default are used.

        Returns:
            WeightEvaluatorScores: Data-structure holding scores on the predictions
                                   and covariate balancing table ("table 1")
        """    

        prediction_scores = Scorer.score_binary_prediction(
            y_true=a_true,
            y_pred_proba=self.weight_for_being_treated,
            y_pred=self.treatment_assignment_pred,
            metrics_to_evaluate=metrics_to_evaluate,
        )
        # Convert single-dtype Series to a row in a DataFrame:
        prediction_scores = pd.DataFrame(prediction_scores).T
        # change dtype of each column to numerical if possible:
        prediction_scores = prediction_scores.apply(pd.to_numeric, errors="ignore")

        covariate_balance = calculate_covariate_balance(X, a_true, self.weight_by_treatment_assignment)

        results = WeightEvaluatorScores(prediction_scores, covariate_balance)
        return results



class WeightEvaluatorPredictions2:
    """Data structure to hold weight-model predictions"""

    def __init__(self, weight_matrix, treatment_assignment, treatment_assignment_prediction=None):
        self.weight_matrix = weight_matrix
        self._treatment_assignment = treatment_assignment
        self.treatment_assignment_prediction = treatment_assignment_prediction

    @property
    def weight_by_treatment_assignment(self):
        weight_by_treatment_assignment = self._extract_vector_from_matrix(self.weight_matrix,
                                                                          self._treatment_assignment)
        return weight_by_treatment_assignment

    @property
    def weight_for_being_treated(self):
        weight_for_being_treated = self._extract_vector_from_matrix(self.weight_matrix,
                                                                    self._treatment_assignment.max())
        return weight_for_being_treated

    @staticmethod
    def _extract_vector_from_matrix(matrix, value):
        if np.isscalar(value):
            vector = matrix[value]
        else:
            # vector = robust_lookup(matrix, value)
            vector = matrix.lookup(value.index, value)
            vector = pd.Series(vector, index=value.index)
        return vector




class WeightPredictor(Predictor):
    def __init__(self, estimator):
        """
        Args:
            estimator (WeightEstimator):
        """
        if not isinstance(estimator, WeightEstimator):
            raise TypeError("WeightEvaluator should be initialized with WeightEstimator, got ({}) instead."
                            .format(type(estimator)))
        self.estimator=estimator

    def _estimator_fit(self, X, a, y=None):
        """ Fit estimator. `y` is ignored.
        """
        self.estimator.fit(X=X, a=a)

    def _estimator_predict(self, X, a):
        """Predict on data.

        Args:
            X (pd.DataFrame): Covariates.
            a (pd.Series): Target variable - treatment assignment

        Returns:
            WeightEvaluatorPredictions
        """
        weight_by_treatment_assignment = self.estimator.compute_weights(X, a, treatment_values=None,
                                                                        use_stabilized=False)
        weight_for_being_treated = self.estimator.compute_weights(X, a, treatment_values=a.max(),
                                                                  use_stabilized=False)
        treatment_assignment_pred = self.estimator.learner.predict(
            X)  # TODO: maybe add predict_label to interface instead
        treatment_assignment_pred = pd.Series(treatment_assignment_pred, index=X.index)

        prediction = WeightEvaluatorPredictions(weight_by_treatment_assignment,
                                                weight_for_being_treated,
                                                treatment_assignment_pred)
        return prediction

    def _estimator_predict2(self, X, a):
        """Predict on data"""
        weight_matrix = self.estimator.compute_weight_matrix(X, a, use_stabilized=False)
        treatment_assignment_pred = self.estimator.learner.predict(
            X)  # TODO: maybe add predict_label to interface instead
        treatment_assignment_pred = pd.Series(treatment_assignment_pred, index=X.index)

        fold_prediction = WeightEvaluatorPredictions2(weight_matrix, a, treatment_assignment_pred)
        return fold_prediction


# #################### #
# Propensity Evaluator #
# #################### #


class PropensityEvaluatorPredictions(WeightEvaluatorPredictions):
    """Data structure to hold propensity-model predictions"""

    def __init__(self, weight_by_treatment_assignment, weight_for_being_treated, treatment_assignment_pred,
                 propensity, propensity_by_treatment_assignment):
        super(PropensityEvaluatorPredictions, self).__init__(weight_by_treatment_assignment,
                                                             weight_for_being_treated,
                                                             treatment_assignment_pred)
        self.propensity = propensity
        self.propensity_by_treatment_assignment = propensity_by_treatment_assignment


class PropensityEvaluatorPredictions2(WeightEvaluatorPredictions2):
    """Data structure to hold propensity-model predictions"""

    def __init__(self, weight_matrix, propensity_matrix, treatment_assignment, treatment_assignment_prediction=None):
        super(PropensityEvaluatorPredictions2, self).__init__(weight_matrix, treatment_assignment,
                                                              treatment_assignment_prediction)
        self.propensity_matrix = propensity_matrix

    @property
    def propensity(self):
        propensity = self._extract_vector_from_matrix(self.propensity_matrix,
                                                      self._treatment_assignment)
        return propensity

    @property
    def propensity_by_treatment_assignment(self):
        # TODO: remove propensity_by_treatment if expected-ROC is not to be used.
        propensity_by_treatment_assignment = self._extract_vector_from_matrix(self.propensity_matrix,
                                                                              self._treatment_assignment.max())
        return propensity_by_treatment_assignment


class PropensityPredictor(WeightPredictor):
    def __init__(self, estimator):
        """
        Args:
            estimator (PropensityEstimator):
        """
        if not isinstance(estimator, PropensityEstimator):
            raise TypeError("PropensityEvaluator should be initialized with PropensityEstimator, got ({}) instead."
                            .format(type(estimator)))
        self.estimator = estimator



    def _estimator_predict(self, X, a):
        """Predict on data.

        Args:
            X (pd.DataFrame): Covariates.
            a (pd.Series): Target variable - treatment assignment

        Returns:
            PropensityEvaluatorPredictions
        """
        propensity = self.estimator.compute_propensity(X, a, treatment_values=a.max())
        propensity_by_treatment_assignment = self.estimator.compute_propensity_matrix(X)
        propensity_by_treatment_assignment = robust_lookup(propensity_by_treatment_assignment, a)

        weight_prediction = super(PropensityPredictor, self)._estimator_predict(X, a)
        # Do not force stabilize=False as in WeightEvaluator:
        weight_by_treatment_assignment = self.estimator.compute_weights(X, a)
        prediction = PropensityEvaluatorPredictions(weight_by_treatment_assignment,
                                                    weight_prediction.weight_for_being_treated,
                                                    weight_prediction.treatment_assignment_pred,
                                                    propensity,
                                                    propensity_by_treatment_assignment)
        return prediction

    def _estimator_predict2(self, X, a):
        """Predict on data."""
        weight_prediction = super(PropensityPredictor, self)._estimator_predict2(X, a)
        propensity_matrix = self.estimator.compute_propensity_matrix(X)
        fold_prediction = PropensityEvaluatorPredictions2(weight_prediction.weight_matrix, propensity_matrix,
                                                          a, weight_prediction.treatment_assignment_prediction)
        return fold_prediction

