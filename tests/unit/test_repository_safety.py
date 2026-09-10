from scripts.check_repository_safety import unsafe_content


def test_credential_signatures_without_exposing_real_secrets():
    assert unsafe_content('gsk_' + 'x' * 40)
    assert unsafe_content('hf_' + 'x' * 25)
    assert unsafe_content('-----BEGIN ' + 'PRIVATE KEY-----')
    assert not unsafe_content('GROQ_API_KEY=\nLLM_MAX_TOKENS=600')
