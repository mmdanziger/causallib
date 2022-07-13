"""Functions that assist with plotting evaluation results."""
import warnings

import numpy as np
from sklearn import metrics

from .plots import get_subplots, lookup_name


def plot_evaluation_results(results, X, a, y, plot_names="all", phase=None, ax=None, **kwargs):
    """Create plot of EvaluationResults.

    Will create as many plots as requested. If multiple plots are requested, creates
    a figure with a subplot for each plot name in `plot_names`. For supported names,
    see `results.all_plot_names`. If `results` have train and validation data, will create
    "train" and "valid" figures. If a single plot is requested, only that plot is created.

    Args:
        results (EvaluationResults): the results to plot, generated by Evaluator
        X (pd.DataFrame): covariates
        a (pd.Series): treatment assignment
        y (pd.Series): outcome
        plot_names (Union[list[str], str], optional): A plot name or list of plot names to plot.
            Depending on the results different names are available. If the special value `"all"`
            is passed, all of the available plots for the given results will be generated.
        phase (Union[str, None], optional): phase to plot "train" or "valid". If not supplied,
            defaults to both for multipanel plot or "train" for single panel plot.
        ax (matplotlib.axis.Axis): Axis to plot single figure on. If plotting multipanel,
            new axes are always created and this argument is ignored.
        **kwargs : passed to plot function if plotting a single panel. Ignored in multipanel mode.
    Returns:
        Union[Dict[str, Dict[str, matplotlib.axis.Axis]], matplotlib.axis.Axis]:
            the Axis objects of the plots in a nested dictionary or the Axis itself if single
            First key is the phase ("train" or "valid") and the second key is the plot name.
    """
    if plot_names == "all":
        plot_names = results.all_plot_names
    elif isinstance(plot_names, str):
        return _make_single_panel_evaluation_plot(
            results=results, X=X, a=a, y=y, plot_name=plot_names, phase=phase, ax=ax, **kwargs
        )
    phases_to_plot = results.predictions.keys() if phase is None else [phase]
    multipanel_plot = {
        plotted_phase: _make_multipanel_evaluation_plot(
            results=results, X=X, a=a, y=y, plot_names=plot_names, phase=plotted_phase
        )
        for plotted_phase in phases_to_plot
    }
    return multipanel_plot


def _make_multipanel_evaluation_plot(results, X, a, y, plot_names, phase):
    phase_fig, phase_axes = get_subplots(len(plot_names))
    named_axes = {}
    phase_axes = phase_axes.ravel()
    # squeeze a vector out of the matrix-like structure of the returned fig.

    # Retrieve all indices of the different folds in the phase [idx_fold_1, idx_folds_2, ...]

    for i, name in enumerate(plot_names):
        ax = phase_axes[i]
        try:
            plot_ax = _make_single_panel_evaluation_plot(
                results, X, a, y, name, phase, ax
            )
        except Exception as e:
            warnings.warn(f"Failed to plot {name} with error {e}")
            plot_ax = None
        named_axes[name] = plot_ax
    phase_fig.suptitle(f"Evaluation on {phase} phase")
    return named_axes


def _make_single_panel_evaluation_plot(results, X, a, y, plot_name, phase, ax=None, **kwargs):
    """Create a single evaluation plot.

    For a single phase and a single plot name.

    Args:
        results (EvaluationResults): evaluation results to plot
        X (pd.DataFrame): covariates
        a (pd.Series): treatment assignment
        y (pd.Series): outcome
        plot_name (str): plot name (from results.all_plot_names)
        phase (str): "train" or "valid"
        ax (matplotlib.axis.Axis, optional): axis to plot on. Defaults to None.
        **kwargs: passed to underlying plotting function
    Raises:
        ValueError: if receives unsupported name

    Returns:
        Union[matplotlib.axis.Axis, None]: axis with plot if successful, else None
    """
    if plot_name not in results.all_plot_names:
        raise ValueError(f"Plot name '{plot_name}' not supported for this result.")
    cv_idx_folds = [
        fold_idx[0] if phase == "train" else fold_idx[1] for fold_idx in results.cv
    ]
    plot_func = lookup_name(plot_name)
    plot_data = results.get_data_for_plot(plot_name, X, a, y, phase=phase)
    # TODO: ^ consider get_data_for_plot returning args (tuple) and kwargs (dictionary)
    #     which will be expanded when calling plot_func: plot_func(*plot_args, **plot_kwargs).
    #     This will allow more flexible specification of param-eters by the caller
    #     For example, Propensity Distribution with kde=True and Weight Distribution with kde=False.
    return plot_func(*plot_data, cv=cv_idx_folds, ax=ax, **kwargs)


def calculate_roc_curve(curve_data):
    """Calculates ROC curve on the folds

    Args:
        curve_data (dict) : dict of curves produced by
            BaseEvaluationPlotDataExtractor.calculate_curve_data
    Returns:
        dict[str, list[np.ndarray]]: Keys being "FPR", "TPR" and "AUC" (ROC metrics)
            and values are a list the size of number of folds with the evaluation of each fold.
    """

    for curve_name in curve_data.keys():
        curve_data[curve_name]["FPR"] = curve_data[curve_name].pop("first_ret_value")
        curve_data[curve_name]["TPR"] = curve_data[curve_name].pop("second_ret_value")
        curve_data[curve_name]["AUC"] = curve_data[curve_name].pop("area")
    return curve_data


def calculate_pr_curve(curve_data, targets):
    """Calculates precision-recall curve on the folds.

    Args:
        curve_data (dict) : dict of curves produced by
            BaseEvaluationPlotDataExtractor.calculate_curve_data
        targets (pd.Series): True labels.

    Returns:
        dict[str, list[np.ndarray]]: Keys being "Precision", "Recall" and "AP" (PR metrics)
            and values are a list the size of number of folds with the
            evaluation of each fold.
            Additional "prevalence" key, with positive-label "prevalence" is added
            to be used by the chance curve.
    """

    for curve_name in curve_data.keys():
        curve_data[curve_name]["Precision"] = curve_data[curve_name].pop(
            "first_ret_value"
        )
        curve_data[curve_name]["Recall"] = curve_data[curve_name].pop(
            "second_ret_value"
        )
        curve_data[curve_name]["AP"] = curve_data[curve_name].pop("area")
    curve_data["prevalence"] = targets.value_counts(normalize=True).loc[targets.max()]
    return curve_data


def calculate_performance_curve_data_on_folds(
    folds_predictions,
    folds_targets,
    sample_weights=None,
    area_metric=metrics.roc_auc_score,
    curve_metric=metrics.roc_curve,
    pos_label=None,
):
    """Calculates performance curves of the predictions across folds.

    Args:
        folds_predictions (list[pd.Series]): Score prediction (as in continuous output
            of classifier, `predict_proba` or `decision_function`) for every fold.
        folds_targets (list[pd.Series]): True labels for every fold.
        sample_weights (list[pd.Series] | None): weight for each sample for every fold.
        area_metric (callable): Performance metric of the area under the curve.
        curve_metric (callable): Performance metric returning 3 output vectors - metric1, metric2
            and thresholds.
            Where metric1 and metric2 depict the curve when plotted on x-axis and y-axis.
        pos_label: What label in `targets` is considered the positive label.

    Returns:
        (list[np.ndarray], list[np.ndarray], list[np.ndarray], list[float]):
            For every fold, the calculated metric1 and metric2 (the curves), the thresholds and the
            area calculations.
    """
    sample_weights = (
        [None] * len(folds_predictions) if sample_weights is None else sample_weights
    )
    # Scikit-learn precision_recall_curve and roc_curve do not return values in a consistent way.
    # Namely, roc_curve returns `fpr`, `tpr`, which correspond to x_axis, y_axis,
    # whereas precision_recall_curve returns `precision`, `recall`,
    # which correspond to y_axis, x_axis.
    # That's why this function will return the values the same order as Scikit's curves,
    # leaving it up to the caller to put labels on what those return values actually are
    # (specifically, whether they're x_axis or y-axis)
    first_ret_folds, second_ret_folds, threshold_folds, area_folds = [], [], [], []
    for fold_prediction, fold_target, fold_weights in zip(
        folds_predictions, folds_targets, sample_weights
    ):
        first_ret_fold, second_ret_fold, threshold_fold = curve_metric(
            fold_target,
            fold_prediction,
            pos_label=pos_label,
            sample_weight=fold_weights,
        )
        try:
            area_fold = area_metric(
                fold_target, fold_prediction, sample_weight=fold_weights
            )
        except ValueError as v:  # AUC cannot be evaluated if targets are constant
            warnings.warn(f"metric {area_metric.__name__} could not be evaluated")
            warnings.warn(str(v))
            area_fold = np.nan

        first_ret_folds.append(first_ret_fold)
        second_ret_folds.append(second_ret_fold)
        threshold_folds.append(threshold_fold)
        area_folds.append(area_fold)
    return area_folds, first_ret_folds, second_ret_folds, threshold_folds
