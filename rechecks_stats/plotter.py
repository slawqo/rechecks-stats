import matplotlib.pyplot as plt

PLOTTER = None


def get_plotter(config):
    global PLOTTER
    if PLOTTER is None:
        PLOTTER = Plotter(config)
    return PLOTTER


class Plotter(object):

    def __init__(self, config):
        self.config = config

    def plot_avg_rechecks(self, plot_points):
        x_values = list(plot_points.keys())
        y_values = list(plot_points.values())
        plt.plot(x_values, y_values,
                 label=('Average number of failed builds '
                        'before patch merge per %s' %
                        self.config.time_window))
        plt.xlabel('patch merge time')
        plt.ylabel('number of failed builds')
        plt.legend()
        plt.xticks(x_values, x_values, rotation='vertical')
        plt.show()

    def plot_patch_rechecks(self, points):
        x_values = [patch['id'] for patch in points]
        y_values = [patch['counter'] for patch in points]
        plt.plot(x_values, y_values,
                 label='Number of failed builds before patch merge')
        plt.xlabel('patch merge time')
        plt.ylabel('number of failed builds')
        plt.legend()
        plt.show()


