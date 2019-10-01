from clld.web.maps import ParameterMap, Map


class NumeralParameterMap(ParameterMap):
    def get_options(self):
        return {
            'base_layer': 'Esri.WorldPhysical',
            'icon_size': 15,
            'max_zoom': 9,
        }

class LanguagesMap(Map):
    def get_options(self):
        return {
            'base_layer': 'Esri.WorldPhysical',
            'icon_size': 15,
            'max_zoom': 9,
        }

def includeme(config):
    config.register_map('parameter', NumeralParameterMap)
    config.register_map('languages', LanguagesMap)
