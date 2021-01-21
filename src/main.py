from flask import Flask, render_template, request, redirect, url_for, Response, flash
import io
import qrcode
import qrcode.image.svg

from modules.coffee import CoffeeUser, coffees_dict
from modules.splitwise import SplitwiseWrapper
from modules.userprovider import UserProvider
from utils import render_error

app = Flask(__name__)
# todo: Set secret key with environment variables
app.secret_key = "xruGtYQfCyAEgMppKxYfHB2x"
userprovider = UserProvider()


@app.route('/')
def index():
    return render_template('index.html', usernames=userprovider.list_usernames())


@app.route('/user/<string:username>')
def coffee_user(username):
    try:
        user = userprovider.get_CoffeeUser(username)
    except KeyError:
        return render_error(404, "User not found!")

    return render_template(
        'coffee/user.html',
        user=user,
        coffees_dict=coffees_dict,
        bill_payed_sum=sum([b.sum for b in user.bills_payed.values()])
    )


@app.route('/user/<string:username>/drink/<string:coffee>')
def coffee_drink(username, coffee):
    try:
        user = userprovider.get_CoffeeUser(username)
    except KeyError:
        return render_error(404, "User not found!")

    coffee = coffees_dict.get(coffee)
    if coffee is None:
        return render_error(404, "Coffee not found!")

    user.current_bill.add(coffee)
    flash(f"{coffee.name} gebucht!", category="success")
    return redirect(url_for('coffee_user', username=user.name))


@app.route('/user/<string:username>/drink/<string:coffee>.svg')
def coffee_drink_qr(username, coffee):
    if username not in userprovider.list_usernames():
        return render_error(404, "User not found!")

    coffee = coffees_dict.get(coffee)
    if coffee is None:
        return render_error(404, "Coffee not found!")

    # Generate **absolute** URL for external access
    url = url_for('coffee_drink', username=username, coffee=coffee.name, _external=True)

    # Use buffer to generate QR code in memory
    with io.BytesIO() as buffer:
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage)
        img.save(buffer)
        qr_svg = buffer.getvalue()

    # Return as SVG with proper mimetype
    return Response(
        qr_svg,
        content_type="image/svg+xml"
    )


@app.route('/user/<string:username>/bill/<string:bill_id>/')
def coffee_bill(username, bill_id):
    """ Detail View: Show single bill """
    try:
        user = userprovider.get_CoffeeUser(username)
    except KeyError:
        return render_error(404, "User not found!")

    bill = user.bills.get(bill_id)
    if bill is None:
        return render_error(404, f"Bill {bill_id} not found!")

    return render_template('coffee/bill.html', bill=bill, user=user)


@app.route('/user/<string:username>/bill/<string:bill_id>/delete/<int:item_id>')
def coffee_bill_delete_item(username: str, bill_id: str, item_id: int):
    return coffee_bill_delete_restore_item(username, bill_id, item_id, "delete")


@app.route('/user/<string:username>/bill/<string:bill_id>/restore/<int:item_id>')
def coffee_bill_restore_item(username: str, bill_id: str, item_id: int):
    return coffee_bill_delete_restore_item(username, bill_id, item_id, "restore")


def coffee_bill_delete_restore_item(username: str, bill_id: str, item_id: int, mode: str):
    """ Delete or restore item from bill """
    # Check that only valid modes are provided
    if mode not in ["delete", "restore"]:
        return render_error(500, f"Incorrect item mode {mode} provided!")

    # Get user
    try:
        user = userprovider.get_CoffeeUser(username)
    except KeyError:
        return render_error(404, "User not found!")

    # Get bill
    bill = user.bills.get(bill_id)
    if bill is None:
        return render_error(404, f"Bill {bill_id} not found!")

    # Delete or restore item
    try:
        if mode == "delete":
            bill.delete(item_id)
        else:
            bill.restore(item_id)
    except IndexError:
        return render_error(404, f"Bill has no item with {item_id}.")

    # Set message according to context
    if mode == "delete":
        msg = f"{bill.items[item_id].coffee.name} als gelöscht markiert und von Summe ausgeschlossen."
    else:
        msg = f"{bill.items[item_id].coffee.name} wiederhergestellt."

    flash(msg, category="success")
    return redirect(url_for('coffee_user', username=user.name))


@app.route('/user/<string:username>/bill/<string:bill_id>/pay')
def coffee_bill_pay(username, bill_id):
    try:
        user = userprovider.get_CoffeeUser(username)
    except KeyError:
        return render_error(404, "User not found!")

    if user.splitwise_id == -1:
        return render_error(401, "User has no splitwise account assigned! Cannot pay bill!")

    bill = user.bills.get(bill_id)
    if bill is None:
        return render_error(404, f"Bill {bill_id} not found!")

    # Only current bill can be payed!
    if not bill == user.current_bill:
        return render_error(403, "You can only pay the current bill!")

    # Trigger transaction on splitwise
    splitwise = SplitwiseWrapper()
    try:
        transaction_id = splitwise.pay_bill(paying_user_id=user.splitwise_id, bill=bill)
    except RuntimeError as e:
        return render_error(500, f"{e}")

    # If successful set id and return to previous page
    user.pay_bill(transaction_id)
    return render_template("coffee/success_bill_payed.html", user=user, msg="Rechnung bezahlt!")


@app.route('/auth/splitwise')
def auth_splitwise():
    splitwise = SplitwiseWrapper()
    redirect_uri = url_for("auth_splitwise_redirect", _external=True)
    url, state = splitwise.s.getOAuth2AuthorizeURL(redirect_uri)
    return redirect(url)


@app.route('/auth/splitwise/redirect')
def auth_splitwise_redirect():
    state = request.args.get('state')
    code = request.args.get('code')

    if state is None or code is None:
        return render_error(
            500,
            "Splitwise authentication failed. Could not find `state` or `code` in response."
        )

    # Save token with SplitwiseWrapper
    splitwise = SplitwiseWrapper()
    redirect_uri = url_for("auth_splitwise_redirect", _external=True)
    token = splitwise.s.getOAuth2AccessToken(code, redirect_uri)
    splitwise.set_access_token(token)

    return redirect(url_for('auth_splitwise_info'))


@app.route('/auth/splitwise/info')
def auth_splitwise_info():
    splitwise = SplitwiseWrapper()

    # Redirect to login if not authenticated
    if splitwise._access_token is None:
        redirect(url_for('auth_splitwise'))

    s_user = splitwise.s.getCurrentUser()
    s_friends = splitwise.s.getFriends()

    # Filter coffee users which are linked to a splitwise id
    splitwise_coffee_users = {
        c.splitwise_id: c
        for c in userprovider.list_CoffeeUsers().values()
        if c.splitwise_id != -1
    }

    return render_template(
        "splitwise/info.html",
        s_user=s_user,
        s_friends=s_friends,
        coffee_users=splitwise_coffee_users
    )


@app.route('/auth/splitwise/logout')
def auth_splitwise_logout():
    splitwise = SplitwiseWrapper()
    splitwise.set_access_token({
        "access_token": "",
        "token_type": ""
    })

    return redirect(url_for('index'))


@app.template_filter('halfmoon_alert_category')
def halfmoon_alert_category(category):
    """ Converts message levels into expression for halfmoon's CSS alert class """
    if category == "error":
        return "danger"
    elif category == "warning":
        return "secondary"
    elif category == "success":
        return "success"
    else:
        return ""
