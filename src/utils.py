from flask import render_template


def render_error(code: int, msg: str):
    """
    Renders standard error template with error code and error message
    """
    return render_template('base/error.html', code=code, msg=msg), code
