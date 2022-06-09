PRINTER = None


def get_printer(config):
    global PRINTER
    if PRINTER is None:
        PRINTER = Printer(config.verbose)
    return PRINTER


class Printer(object):

    def __init__(self, verbose):
        self.verbose = verbose

    def log_error(self, msg):
        print(msg)

    def log_debug(self, msg):
        if self.verbose:
            print(msg)
