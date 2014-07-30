import qraat

from django import template
register = template.Library()

@register.filter(name='google_maps_api')
def google_maps_api(value):
  try:
    api = qraat.csv.csv(os.environ['RMG_SERVER_UI_KEYS']).get(name='google_maps_js_api')
    return api.key

  except KeyError:
    raise qraat.error.QraatError("undefined environment variables. Try `source rmg_env`")
  
  except IOError, e:
    raise qraat.error.QraatError("missing DB credential file '%s'" % e.filename)

