from app.auth.password import SCRYPT_N, hash_password, verify_password

FAKE_PASSWORD = "test password only 1"  # fake data (ENG-047)


def test_arch_030_password_hash_verifies_and_hides_the_password():
    stored = hash_password(FAKE_PASSWORD)
    assert FAKE_PASSWORD not in stored
    assert verify_password(FAKE_PASSWORD, stored)
    assert not verify_password("test password only 2", stored)


def test_arch_030_same_password_hashes_differently_each_time():
    assert hash_password(FAKE_PASSWORD) != hash_password(FAKE_PASSWORD)


def test_arch_030_hash_keeps_its_parameters():
    # A later change to SCRYPT_N still verifies passwords saved before it.
    scheme, n, *_ = hash_password(FAKE_PASSWORD).split("$")
    assert (scheme, int(n)) == ("scrypt", SCRYPT_N)


def test_arch_030_unknown_scheme_is_refused():
    stored = hash_password(FAKE_PASSWORD).replace("scrypt", "plain", 1)
    assert not verify_password(FAKE_PASSWORD, stored)
