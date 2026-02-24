class BaseStrategy:
    """
    Base class for Uno strategies.
    """
    def choose_card(self, hand, top_card, current_color):
        raise NotImplementedError