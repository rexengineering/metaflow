from typing import Any, Callable, Dict
from urllib.parse import urlencode

from quart import Quart, request, make_response


def wrap(
        module_dict: Dict[str, Any],
        service_task_function: Callable[[Dict[str, Any]], Dict]):
    app = Quart(module_dict.get('__name__', __name__))

    # Create a GET method handler.
    @app.route('/', methods=['GET'])
    async def handle_get():
        return service_task_function(request.args.to_dict())

    # Create a POST method handler.
    @app.route('/', methods=['POST'])
    async def handle_post():
        if request.is_json:
            return service_task_function(await request.json)
        form = await request.form
        environment = service_task_function(form.to_dict())
        return await make_response(
            urlencode(environment), {'Content-Type': 'x-www-form-urlencoded'}
        )

    # Return the resulting application.
    return app


if __name__ == '__main__':
    def test_function(environment):
        print(environment)
        hello = f'Hello, {environment.get("name", "world")}.\n'
        print(hello)
        environment['hello'] = hello
        return environment
    app = wrap(globals(), test_function)
    app.run('localhost', debug=True)
