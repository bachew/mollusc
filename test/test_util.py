# -*- coding: utf-8 -*-
from mollusc import util


def test_list_not_str():
    assert util.list_not_str(None) is None
    assert util.list_not_str('string') == ['string']
    assert util.list_not_str(('a', 'b')) == ['a', 'b']
    assert util.list_not_str(['c', 'd']) == ['c', 'd']
    assert util.list_not_str({'e': 'f'}) == ['e']
    assert util.list_not_str(util) == [util]
