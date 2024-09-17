


from flask import current_app

import cea.config
import cea.inputlocator


def deconstruct_parameters(p: cea.config.Parameter):
    params = {'name': p.name, 'type': type(p).__name__, 'nullable': False, 'help': p.help}
    try:
        params["value"] = p.get()
    except cea.ConfigError as e:
        print(e)
        params["value"] = ""

    if isinstance(p, cea.config.ChoiceParameter):
        params['choices'] = p._choices

    if isinstance(p, cea.config.WeatherPathParameter):
        config = current_app.cea_config
        locator = cea.inputlocator.InputLocator(config.scenario)
        params['choices'] = {wn: locator.get_weather(
            wn) for wn in locator.get_weather_names()}

    elif isinstance(p, cea.config.DatabasePathParameter):
        params['choices'] = p._choices

    if hasattr(p, "_extensions") or hasattr(p, "extensions"):
        params["extensions"] = getattr(p, "_extensions", None) or getattr(p, "extensions")

    try:
        params["nullable"] = p.nullable
    except AttributeError as e:
        pass

    return params