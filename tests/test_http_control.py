from unittest.mock import MagicMock, patch

import pytest
import requests

from nomix_clicker import Clicker, ControlError
from nomix_clicker import api_helper


@pytest.fixture
def http():
    response = MagicMock(status_code=200)
    response.json.return_value = {'success': True, 'status': 'sent', 'device_acknowledged': False}
    with patch.object(api_helper.session, 'post', return_value=response) as post, patch.object(api_helper, 'get_api_url', return_value='https://node.invalid/clicker/v1'):
        yield post, response


def test_default_clicker_uses_http_without_connection_setup(http):
    post, _ = http
    with patch('nomix_clicker.clicker.ControlSession') as connect:
        result = Clicker('Device').click((100, 200))
    connect.assert_not_called()
    assert result['success'] and not result['device_acknowledged']
    post.assert_called_once_with('https://node.invalid/clicker/v1/Device/tap', json={'left': 100, 'top': 200, 'duration': 100}, timeout=10.1)


def test_classic_helpers_keep_their_names_defaults_and_http_parameters(http):
    post, _ = http
    api_helper.move('Device', (1, 2), (3, 4))
    assert post.call_args.kwargs['json'] == {'start_left': 1, 'start_top': 2, 'end_left': 3, 'end_top': 4, 'is_pressed': False, 'duration': 300}
    api_helper.double_tap('Device', (1, 2))
    assert post.call_args.args[0].endswith('/double-tap')
    assert post.call_args.kwargs['json']['duration'] == 50
    api_helper.type_text('Device', 'Hello')
    assert post.call_args.args[0].endswith('/keyboard/type')
    assert post.call_args.kwargs['timeout'] >= 200


def test_http_busy_stops_macro_without_retry(http):
    post, response = http
    response.status_code = 409
    response.json.return_value = {'detail': {'code': -32002, 'message': 'busy', 'outcome': 'not_sent'}}
    with pytest.raises(ControlError) as error:
        Clicker('Device').click((1, 2))
    assert error.value.outcome == 'not_sent'
    assert post.call_count == 1


def test_http_lost_response_is_unknown_and_never_retried(http):
    post, _ = http
    post.side_effect = requests.ReadTimeout('lost')
    with pytest.raises(ControlError) as error:
        api_helper.tap('Device', (1, 2))
    assert error.value.outcome == 'unknown'
    assert post.call_count == 1


def test_failed_exclusive_session_never_falls_back_to_http(http):
    post, _ = http
    clicker = Clicker('Device')
    clicker.control = MagicMock()
    clicker.control.request.side_effect = ControlError(-32007, 'connection lost', 'unknown')
    with pytest.raises(ControlError):
        clicker.click((1, 2))
    post.assert_not_called()
    clicker.close()
    with pytest.raises(ControlError):
        clicker.click((1, 2))
    post.assert_not_called()


@pytest.mark.parametrize('payload', [None, [], {'success': False}, {'status': 'sent'}])
def test_unrecognized_http_result_never_claims_success(http, payload):
    post, response = http
    response.json.return_value = payload
    with pytest.raises(ControlError) as error:
        Clicker('Device').click((1, 2))
    assert error.value.outcome == 'unknown' and post.call_count == 1
