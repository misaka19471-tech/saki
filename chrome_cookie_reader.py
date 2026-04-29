# -*- coding: utf-8 -*-
"""Windows Chrome Cookie 读取器 —— 绕过文件锁 + AES-GCM 解密"""

import os, json, ctypes, ctypes.wintypes, base64, sqlite3

# ============================================================
# Chrome 解密密钥提取 (DPAPI)
# ============================================================

def _get_chrome_key():
    local_state = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Local State')
    with open(local_state, 'r', encoding='utf-8') as f:
        enc_key_b64 = json.load(f)['os_crypt']['encrypted_key']
    enc_key = base64.b64decode(enc_key_b64)[5:]  # 去掉 "DPAPI" 前缀

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

    bi = DATA_BLOB(len(enc_key), ctypes.cast(ctypes.create_string_buffer(enc_key, len(enc_key)), ctypes.POINTER(ctypes.c_char)))
    bo = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(bi), None, None, None, None, 0, ctypes.byref(bo)):
        raise OSError('CryptUnprotectData failed')
    key = ctypes.string_at(bo.pbData, bo.cbData)
    ctypes.windll.kernel32.LocalFree(bo.pbData)
    return key


# ============================================================
# 绕过文件锁读取 SQLite (Windows API)
# ============================================================

def _copy_locked_db(src, dst):
    GENERIC_READ = 0x80000000
    FILE_SHARE_ALL = 0x00000007  # FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateFileW(src, GENERIC_READ, FILE_SHARE_ALL,
                                   None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
    if handle == -1 or handle == 0xFFFFFFFF:
        err = kernel32.GetLastError()
        raise OSError(f'CreateFileW failed, error code: {err}')

    try:
        size_high = ctypes.wintypes.DWORD()
        size_low = kernel32.GetFileSize(handle, ctypes.byref(size_high))
        if size_low == 0xFFFFFFFF:
            raise OSError('GetFileSize failed')
        total_size = size_low  # 文件 < 4GB
        buf = ctypes.create_string_buffer(total_size)
        bytes_read = ctypes.wintypes.DWORD()
        if not kernel32.ReadFile(handle, buf, total_size, ctypes.byref(bytes_read), None):
            raise OSError('ReadFile failed')
        with open(dst, 'wb') as f:
            f.write(buf.raw[:bytes_read.value])
    finally:
        kernel32.CloseHandle(handle)


# ============================================================
# AES-GCM 解密 (Chrome v80+)
# ============================================================

def _decrypt_cookie(encrypted_value, key):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aes = AESGCM(key)
    nonce = encrypted_value[3:15]
    ciphertext = encrypted_value[15:]
    return aes.decrypt(nonce, ciphertext, None).decode('utf-8', errors='ignore')


# ============================================================
# 主入口
# ============================================================

def read_bilibili_cookie():
    """返回 'SESSDATA=xxx; bili_jct=xxx; ...' 格式的 Cookie 字符串"""
    try:
        key = _get_chrome_key()
    except Exception as e:
        raise RuntimeError(f'获取解密密钥失败: {e}')

    db_path = os.path.join(
        os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data'),
        'Default', 'Network', 'Cookies'
    )
    if not os.path.isfile(db_path):
        db_path = os.path.join(
            os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data'),
            'Default', 'Network', 'Cookies'
        )

    tmp = db_path + '.cookie_reader_tmp'

    try:
        _copy_locked_db(db_path, tmp)
        conn = sqlite3.connect(tmp)
        rows = conn.execute(
            "SELECT name, encrypted_value FROM cookies WHERE host_key LIKE '%bilibili.com'"
        ).fetchall()
        conn.close()

        needed = {'SESSDATA', 'bili_jct', 'DedeUserID', 'DedeUserID__ckMd5', 'sid', 'buvid3', 'buvid4'}
        pairs = {}
        for name, enc_val in rows:
            if name in needed:
                try:
                    val = _decrypt_cookie(enc_val, key)
                    pairs[name] = val
                except Exception:
                    pass

        if not pairs:
            # 尝试 Edge 浏览器
            db_path = os.path.join(
                os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data'),
                'Default', 'Network', 'Cookies'
            )
            _copy_locked_db(db_path, tmp)
            conn = sqlite3.connect(tmp)
            rows = conn.execute(
                "SELECT name, encrypted_value FROM cookies WHERE host_key LIKE '%bilibili.com'"
            ).fetchall()
            conn.close()
            for name, enc_val in rows:
                if name in needed:
                    try:
                        val = _decrypt_cookie(enc_val, key)
                        pairs[name] = val
                    except Exception:
                        pass

        if 'SESSDATA' not in pairs:
            return ''

        return '; '.join(f'{k}={v}' for k, v in pairs.items())

    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


if __name__ == '__main__':
    cookie = read_bilibili_cookie()
    if cookie:
        print(f'OK: {cookie[:300]}')
    else:
        print('FAILED: No SESSDATA found')
