"""Mixins for plotting.

To work the mixin requires the class to implement `get_data_for_plot` with the
supported plot names. See .data_extractors for examples. """

from . import plots


class WeightPlotterMixin:
    """Mixin to add members to for weight estimation plotting.

    Class must implement:
      * `get_data_for_plot(plots.COVARIATE_BALANCE_GENERIC_PLOT)`
      * `get_data_for_plot(plots.WEIGHT_DISTRIBUTION_PLOT)`
    """
    def plot_covariate_balance(
        self,
        kind="love",
        phase="train",
        ax=None,
        aggregate_folds=True,
        thresh=None,
        plot_semi_grid=True,
        **kwargs,
    ):
        (table1_folds,) = self.get_data_for_plot(
            plots.COVARIATE_BALANCE_GENERIC_PLOT, phase=phase
        )
        if kind == "love":
            return plots.plot_mean_features_imbalance_love_folds(
                table1_folds=table1_folds,
                ax=ax,
                aggregate_folds=aggregate_folds,
                thresh=thresh,
                plot_semi_grid=plot_semi_grid,
                **kwargs,
            )
        if kind == "slope":
            return plots.plot_mean_features_imbalance_slope_folds(
                table1_folds=table1_folds,
                ax=ax,
                thresh=thresh,
                **kwargs,
            )

    def plot_weight_distribution(
        self,
        phase="train",
        reflect=True,
        kde=False,
        cumulative=False,
        norm_hist=True,
        ax=None,
    ):
        """
        Plot the distribution of propensity score.

        Args:
            propensity (pd.Series):
            treatment (pd.Series):
            reflect (bool): Whether to plot treatment groups on opposite sides of the x-axis.
                This can only work if there are exactly two groups.
            kde (bool): Whether to plot kernel density estimation
            cumulative (bool): Whether to plot cumulative distribution.
            norm_hist (bool): If False - use raw counts on the y-axis.
                            If kde=True, then norm_hist should be True as well.
            ax (plt.Axes | None):

        Returns:

        """
        weights, treatments, cv = self.get_data_for_plot(
            plots.WEIGHT_DISTRIBUTION_PLOT, phase=phase
        )

        return plots.plot_propensity_score_distribution_folds(
            predictions=weights,
            hue_by=treatments,
            cv=cv,
            reflect=reflect,
            kde=kde,
            cumulative=cumulative,
            norm_hist=norm_hist,
            ax=ax,
        )


class ClassificationPlotterMixin:
    """Mixin to add members to for classification/binary prediction estimation.

    This occurs for propensity models (treatment assignment is inherently binary)
    and for outcome models where the outcome is binary.

    Class must implement:
      * `get_data_for_plot(plots.ROC_CURVE_PLOT)`
      * `get_data_for_plot(plots.PR_CURVE_PLOT)`
      * `get_data_for_plot(plots.CALIBRATION_PLOT)`
    """
    def plot_roc_curve(
        self,
        phase="train",
        plot_folds=False,
        label_folds=False,
        label_std=False,
        ax=None,
    ):
        (roc_curve_data,) = self.get_data_for_plot(plots.ROC_CURVE_PLOT, phase=phase)
        return plots.plot_roc_curve_folds(
            roc_curve_data,
            ax=ax,
            plot_folds=plot_folds,
            label_folds=label_folds,
            label_std=label_std,
        )

    def plot_pr_curve(
        self,
        phase="train",
        plot_folds=False,
        label_folds=False,
        label_std=False,
        ax=None,
    ):
        (pr_curve_data,) = self.get_data_for_plot(plots.PR_CURVE_PLOT, phase=phase)
        return plots.plot_precision_recall_curve_folds(
            pr_curve_data,
            ax=ax,
            plot_folds=plot_folds,
            label_folds=label_folds,
            label_std=label_std,
        )

    def plot_calibration_curve(
        self,
        phase="train",
        n_bins=10,
        plot_se=True,
        plot_rug=False,
        plot_histogram=False,
        quantile=False,
        ax=None,
    ):
        """Plot calibration curves for multiple models (presumably in folds)

        Args:
            predictions (list[pd.Series]): list (each entry of a fold) of arrays
                - probability ("scores") predictions.
            targets (pd.Series): true labels to calibrate against on the overall
                data (not divided to folds).
            cv (list[np.array]):
            n_bins (int): number of bins to evaluate in the plot
            plot_se (bool): Whether to plot standard errors around the mean
                bin-probability estimation.
            plot_rug (bool):
            plot_histogram (bool):
            quantile (bool): If true, the binning of the calibration curve is by quantiles. Default is false
            ax (plt.Axes): Optional

        Note:
            One of plot_propensity or plot_model must be True.

        Returns:

        """
        predictions, targets, cv = self.get_data_for_plot(
            plots.CALIBRATION_PLOT, phase=phase
        )
        return plots.plot_calibration_folds(
            predictions=predictions,
            targets=targets,
            cv=cv,
            n_bins=n_bins,
            plot_se=plot_se,
            plot_rug=plot_rug,
            plot_histogram=plot_histogram,
            quantile=quantile,
            ax=ax,
        )


class ContinuousOutcomePlotterMixin:
    """Mixin to add members to for continous outcome estimation.

    Class must implement:
      * `get_data_for_plot(plots.CONTINUOUS_ACCURACY_PLOT)`
      * `get_data_for_plot(plots.RESIDUALS_PLOT)`
      * `get_data_for_plot(plots.CONTINUOUS_ACCURACY_PLOT)`
    """    
    def plot_continuous_accuracy(
        self, phase="train", alpha_by_density=True, plot_residuals=False, ax=None
    ):
        predictions, y, a, cv = self.get_data_for_plot(
            plots.CONTINUOUS_ACCURACY_PLOT, phase=phase
        )
        return plots.plot_continuous_prediction_accuracy_folds(
            predictions=predictions,
            y=y,
            a=a,
            cv=cv,
            alpha_by_density=alpha_by_density,
            plot_residuals=plot_residuals,
            ax=ax,
        )

    def plot_residuals(self, phase="train", alpha_by_density=True, ax=None):
        predictions, y, a, cv = self.get_data_for_plot(plots.RESIDUALS_PLOT, phase=phase)
        return plots.plot_residual_folds(
            predictions=predictions,
            y=y,
            a=a,
            cv=cv,
            alpha_by_density=alpha_by_density,
            ax=ax,
        )

    def plot_common_support(self, phase="train", alpha_by_density=True, ax=None):
        """Plot the scatter plot of y0 vs. y1 for multiple scoring results, colored by the treatment

        Args:
            alpha_by_density (bool): Whether to calculate points alpha value (transparent-opaque)
               with density estimation. This can take some time to compute for a large number
               of points. If False, alpha calculation will be a simple fast heuristic.
            ax (plt.Axes): The axes on which the plot will be displayed. Optional.
        """
        predictions, treatments, cv = self.get_data_for_plot(
            plots.COMMON_SUPPORT_PLOT, phase=phase
        )
        return plots.plot_counterfactual_common_support_folds(
            predictions=predictions,
            hue_by=treatments,
            cv=cv,
            alpha_by_density=alpha_by_density,
            ax=ax,
        )
