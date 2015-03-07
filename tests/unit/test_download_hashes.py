import pytest

from pip.download import _get_hash_from_file, _check_hash
from pip.exceptions import InstallationError
from pip.index import Link


def test_get_hash_from_file_md5(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#md5=d41d8cd98f00b204e9800998ecf8427e"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    assert download_hash.digest_size == 16
    assert download_hash.hexdigest() == "d41d8cd98f00b204e9800998ecf8427e"


def test_get_hash_from_file_sha1(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha1=da39a3ee5e6b4b0d3255bfef95601890afd80709"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    assert download_hash.digest_size == 20
    assert download_hash.hexdigest() == (
        "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    )


def test_get_hash_from_file_sha224(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha224=d14a028c2a3a2bc9476102bb288234c415a2b01f828ea62ac5b3e42f"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    assert download_hash.digest_size == 28
    assert download_hash.hexdigest() == (
        "d14a028c2a3a2bc9476102bb288234c415a2b01f828ea62ac5b3e42f"
    )


def test_get_hash_from_file_sha384(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha384=38b060a751ac96384cd9327eb1b1e36a21fdb71114be07434c0cc7bf63f6e"
        "1da274edebfe76f65fbd51ad2f14898b95b"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    assert download_hash.digest_size == 48
    assert download_hash.hexdigest() == (
        "38b060a751ac96384cd9327eb1b1e36a21fdb71114be07434c0cc7bf63f6e1da274e"
        "debfe76f65fbd51ad2f14898b95b"
    )


def test_get_hash_from_file_sha256(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852"
        "b855"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    assert download_hash.digest_size == 32
    assert download_hash.hexdigest() == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_get_hash_from_file_sha512(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha512=cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36"
        "ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    assert download_hash.digest_size == 64
    assert download_hash.hexdigest() == (
        "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0"
        "d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
    )


def test_get_hash_from_file_unknown(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#unknown_hash=d41d8cd98f00b204e9800998ecf8427e"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    assert download_hash is None


def test_check_hash_md5_valid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#md5=d41d8cd98f00b204e9800998ecf8427e"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    _check_hash(download_hash, file_link)


def test_check_hash_md5_invalid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link("http://testserver/gmpy-1.15.tar.gz#md5=deadbeef")

    download_hash = _get_hash_from_file(file_path, file_link)

    with pytest.raises(InstallationError):
        _check_hash(download_hash, file_link)


def test_check_hash_sha1_valid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha1=da39a3ee5e6b4b0d3255bfef95601890afd80709"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    _check_hash(download_hash, file_link)


def test_check_hash_sha1_invalid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link("http://testserver/gmpy-1.15.tar.gz#sha1=deadbeef")

    download_hash = _get_hash_from_file(file_path, file_link)

    with pytest.raises(InstallationError):
        _check_hash(download_hash, file_link)


def test_check_hash_sha224_valid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha224=d14a028c2a3a2bc9476102bb288234c415a2b01f828ea62ac5b3e42f'"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    _check_hash(download_hash, file_link)


def test_check_hash_sha224_invalid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link("http://testserver/gmpy-1.15.tar.gz#sha224=deadbeef")

    download_hash = _get_hash_from_file(file_path, file_link)

    with pytest.raises(InstallationError):
        _check_hash(download_hash, file_link)


def test_check_hash_sha384_valid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha384=38b060a751ac96384cd9327eb1b1e36a21fdb71114be07434c0cc7bf63f6"
        "e1da274edebfe76f65fbd51ad2f14898b95b"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    _check_hash(download_hash, file_link)


def test_check_hash_sha384_invalid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link("http://testserver/gmpy-1.15.tar.gz#sha384=deadbeef")

    download_hash = _get_hash_from_file(file_path, file_link)

    with pytest.raises(InstallationError):
        _check_hash(download_hash, file_link)


def test_check_hash_sha256_valid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b785"
        "2b855"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    _check_hash(download_hash, file_link)


def test_check_hash_sha256_invalid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link("http://testserver/gmpy-1.15.tar.gz#sha256=deadbeef")

    download_hash = _get_hash_from_file(file_path, file_link)

    with pytest.raises(InstallationError):
        _check_hash(download_hash, file_link)


def test_check_hash_sha512_valid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha512=cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36c"
        "e9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    _check_hash(download_hash, file_link)


def test_check_hash_sha512_invalid(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link("http://testserver/gmpy-1.15.tar.gz#sha512=deadbeef")

    download_hash = _get_hash_from_file(file_path, file_link)

    with pytest.raises(InstallationError):
        _check_hash(download_hash, file_link)


def test_check_hasher_mismsatch(data):
    file_path = data.packages.join("gmpy-1.15.tar.gz")
    file_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#md5=d41d8cd98f00b204e9800998ecf8427e"
    )
    other_link = Link(
        "http://testserver/gmpy-1.15.tar.gz"
        "#sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b785"
        "2b855"
    )

    download_hash = _get_hash_from_file(file_path, file_link)

    with pytest.raises(InstallationError):
        _check_hash(download_hash, other_link)
