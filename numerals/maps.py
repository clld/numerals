from clld.web.maps import ParameterMap, Map


class NumeralParameterMap(ParameterMap):
    def get_options(self):
        return {
            'icon_size': 15,
            'max_zoom': 10,
        }


class NumeralLanguagesMap(Map):
    def get_options(self):
        return {
            'icon_size': 15,
            'max_zoom': 10,
            'info_query': {'map_pop_up': 1},
        }


def includeme(config):
    config.register_map('parameter', NumeralParameterMap)
    config.register_map('languages', NumeralLanguagesMap)
