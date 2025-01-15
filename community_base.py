#!/usr/bin/env python3
# -*- coding: utf-8 -*-

r''' This text is easier to read when the markdown is parsed: <https://github.com/Harding-Stardust/community_base/blob/main/README.md>

# Summary
This Python script will help you develop scripts for [Hexrays IDA Pro](https://hex-rays.com/ida-pro)
community_base turns IDA Python into a [DWIM (Do What I Mean)](https://en.wikipedia.org/wiki/DWIM) style and I try to follow ["Principle of least astonishment"](https://en.wikipedia.org/wiki/Principle_of_least_astonishment)

You can think of this script as padding between the user created scripts and the IDA Python API.
If you develop scripts with this script as base, then if (when) Hexrays change something in their API, instead of fixing EVERY script out there
the community can fix this script and all the user created scripts (that depends on this script) will work again.

I try to have a low cognitive load. "What matters is the amount of confusion developers feel when going through the code." Quote from <https://minds.md/zakirullin/cognitive>

# Why you should use this script
- Easier to write plugins and scripts for IDA Python
- Type hints on everything! 
- Strong typing. I use [Pydantic](https://docs.pydantic.dev/latest/) to force types. This makes the code much easier to read since you get an idea what a function expects and what it returns. I try to follow [PEP 484](https://peps.python.org/pep-0484/) as much as I can.
- Full function/variable names. This makes variables and functions easy to read at a glance.
- Properly documented. I try to document as extensive I can without making redundent comments.
- Easy to debug (hopefully!). All functions that are non-trivial have the last argument named ```arg_debug``` which is a bool that if set, prints out helpful information on what is happening in the code.
- Good default values set. E.g. ```ida_idp.assemble(ea, 0, ea, True, 'mov eax, 1')``` have many arguments you don't know that they should be.
- Understands what the user wants. I have type checks and treat input different depending on what you send in. E.g. addresses vs labels. In my script, everywhere you are expecting an address, you can send in a label (or register) that is then resolved. See ```address()``` and ```eval_expression()``` (same with where tinfo_t (type info) is expected, you can also send in a C-type string)
- I have written the code as easy I can to READ (hopefully), it might not be the most Pythonic way (or the fastest) but I have focused on readability. However, I do understand that this is subjective.
- Do _NOT_ conflict with other plugins. I am very careful to only overwrite things like docstrings, otherwise I add to the classes that are already in the IDA Python
- I have wrappers around some of IDAs Python APIs that actually honors the type hints they have written. You can find them with this simple code:
```python
[wrapper for wrapper in dir(community_base) if wrapper.startswith("_idaapi_")]
```
- Cancel scripts that take too long. You can copy the the string "abort.ida" into the clipboard and within 30 seconds, the script will stop. Check out ```_check_if_long_running_script_should_abort()``` for implementation
- Easy bug reporting. See the function ```bug_report()```
- Get some good links to helpful resources. See the function ```links()```
- when developing, it's nice to have a fast and easy way to reload the script and all it's dependencies, see the function ```reload_module()```
- Load shellcode into the running process. See ```load_file_into_memory()``` using [AppCall](https://www.youtube.com/watch?v=GZUHXkV0vdM)
- Help with [AppCall](https://www.youtube.com/watch?v=GZUHXkV0vdM) to call functions that are inside the executable. (Think of decrypt functions) E.g. ```win_LoadLibraryA()```
- Simple and fast way to get info about APIs, see ```google()```
- 3 new hotkeys:
- - w --> marked bytes will be dumped to disk
- - alt + Ins --> Copy current address into clipboard (same as [x64dbg](https://x64dbg.com/))
- - shift + c --> Copy selected bytes into clipboard as hex text (same as [x64dbg](https://x64dbg.com/))
- Much more that I can't think of right now as I need to publish this script before new years eve!

# Installation
To use this script, put is somewhere that IDA can find it. A good place is this filename:
```python
import idaapi
print(idaapi.__file__.replace("idaapi.py", "community_base.py"))
```
It is strongly advised to edit your idapythonrc.py which can be found by typing the following in IDA:
```python
import idaapi
import os
print(os.path.join(idaapi.get_user_idadir(), "idapythonrc.py"))
```
and to get easy access to this script, add the line:
```python
import community_base as cb
```
Read more: <https://hex-rays.com/blog/igors-tip-of-the-week-33-idas-user-directory-idausr>


# Tested with
```Windows 10 + IDA 9.0 + Python 3.12``` and ```Windows 10 + IDA 8.4 + Python 3.8```

# Future
- I have not had the time to polish everything as much as I would have liked. Keep an eye on this repo and things will get updated!
- I'm planning on doing some short clips on how the script is supposed to be used, this takes time and video editing is not my strong side
- Need help with more testing
- More of everything :-D
'''
__version__ = "2025-01-16 00:54:23"
__author__ = "Harding (https://github.com/Harding-Stardust)"
__description__ = __doc__
__copyright__ = "Copyright 2025"
__credits__ = ["https://www.youtube.com/@allthingsida",
               "https://github.com/grayhatacademy/ida/blob/master/plugins/shims/ida_shims.py",
               "https://github.com/arizvisa/ida-minsc",
               "https://github.com/Shizmob/ida-tools",
               "https://github.com/synacktiv/bip/",
               "https://github.com/tmr232/Sark"]
__license__ = "GPL 3.0"
__maintainer__ = "Harding (https://github.com/Harding-Stardust)"
__email__ = "not.at.the.moment@example.com"
__status__ = "Development"
__url__ = "https://github.com/Harding-Stardust/community_base"

import os # https://peps.python.org/pep-0008/#imports
import sys
import re
import time
import datetime
import ctypes
import json # TODO: Change to json5?
from typing import Union, List, Dict, Tuple, Any, Optional, Callable
from types import ModuleType
import inspect as _inspect
from pydantic import validate_call

try:
    import chardet
except ImportError:
    print(f"{__file__}: Missing import chardet, this module is used to guess string encoding. It's nice to have, not need to have. pip install chardet")

import ida_allins as _ida_allins # type: ignore[import-untyped]
import ida_auto as _ida_auto # type: ignore[import-untyped]
import ida_bytes as _ida_bytes # type: ignore[import-untyped]
import ida_dbg as _ida_dbg # type: ignore[import-untyped]
import ida_funcs as _ida_funcs # type: ignore[import-untyped]
import ida_hexrays as _ida_hexrays # type: ignore[import-untyped]
import ida_idaapi as _ida_idaapi # type: ignore[import-untyped]
import ida_ida as _ida_ida # type: ignore[import-untyped]
import ida_idc as _ida_idc # type: ignore[import-untyped]
import ida_idd as _ida_idd # type: ignore[import-untyped] # The interface consists of structures describing the target debugged processor and a debugging API. https://python.docs.hex-rays.com/namespaceida__idd.html
import ida_idp as _ida_idp # type: ignore[import-untyped] # The interface consists of two structures: definition of target assembler: ::ash and definition of current processor: ::ph. These structures contain information about target processor and assembler features.
import ida_kernwin as _ida_kernwin # type: ignore[import-untyped]
import ida_lines as _ida_lines # type: ignore[import-untyped]
import ida_loader as _ida_loader # type: ignore[import-untyped]
import ida_name as _ida_name # type: ignore[import-untyped]
import ida_nalt as _ida_nalt # type: ignore[import-untyped] # Definitions of various information kept in netnodes. Each address in the program has a corresponding netnode: netnode(ea).
import ida_netnode as _ida_netnode # type: ignore[import-untyped] # Functions that provide the lowest level public interface to the database.
import ida_pro as _ida_pro # type: ignore[import-untyped]
import ida_range as _ida_range # type: ignore[import-untyped]
import ida_segment as _ida_segment # type: ignore[import-untyped]
import idc as _idc # type: ignore[import-untyped]
import ida_typeinf as _ida_typeinf # type: ignore[import-untyped]
import ida_ua as _ida_ua # type: ignore[import-untyped] # ua stands for UnAssembly (I think...)  Functions that deal with the disassembling of program instructions. https://python.docs.hex-rays.com/namespaceida__ua.html
import ida_xref as _ida_xref # type: ignore[import-untyped]
import idautils as _idautils # type: ignore[import-untyped]
import ida_diskio as _ida_diskio # type: ignore[import-untyped]
from PyQt5.Qt import QApplication # type: ignore[import-untyped]

HOTKEY_DUMP_TO_DISK = 'w' # Select bytes and press w to dump it to disk in the same directory as the IDB. One can also call dump_to_disk(address, length) to dump from the console
HOTKEY_COPY_SELECTED_BYTES_AS_HEX_TEXT = 'shift-c' # Select bytes and press Shift-C to copy the marked bytes as hex text. Same shortcut as in x64dbg.
HOTKEY_COPY_CURRENT_ADDRESS = 'alt-ins' # Copy the current address as hex text into the clipboard. Same shortcut as x64dbg.

BufferType = Union[str, bytes, bytearray, List[str], List[bytes], List[bytearray]]

# EvaluateType is anything that can be evalutad to an int. E.g. the address() function can take this type and then try to resolve an adress. Give it a str (a label) and it will work, give it a ida_segment.segment_t object and it will give the address to the start of the segment
EvaluateType = Union[str, int, _ida_idp.reg_info_t, _ida_ua.insn_t, _ida_hexrays.cinsn_t, _ida_hexrays.cfuncptr_t, _ida_funcs.func_t, _ida_idaapi.PyIdc_cvt_int64__, _ida_segment.segment_t, _ida_ua.op_t, _ida_typeinf.funcarg_t, _idautils.Strings.StringItem, _ida_dbg.bpt_t, _ida_idd.modinfo_t, _ida_hexrays.carg_t, _ida_hexrays.cexpr_t, _ida_range.range_t]
__GLOBAL_LOG_EVERYTHING = False # If this is set to True, then all calls to log_print() will be printed, this can cause massive logs but good for hard to find bugs

# HELPERS ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def links(arg_open_browser_at_official_python_docs: bool = False) -> Dict[str, Dict[str, str]]:
    ''' Various information to help you develop your own scripts.

        Read more: https://python.docs.hex-rays.com/
       '''
    l_abbreviations = {
        'ASG': "Assign",
        'BPU': "Bytes Per Unit",
        'CC' : "Calling Convention",
        'EA' : "Effective Address, just an address in the process",
        'MBA': "Microcode",
        'PEB': "Process Environment Block",
        'TEB': "Thread Environment Block, a.k.a. TIB (Thread Information Block)",
        'TIB': "Thread Information Block, a.k.a. TEB (Thread Environment Block)",
        'tid': 'Type ID',
        'TIF': "type info. E.g. int*, wchar_t* and so on",
        'TIL': "Type Information Library, IDAs internal name for it's database with types in it. It's like a huge .h file but in IDAs own format"
        }

    l_links = {}
    l_links["official_python_documentation"] =      "https://python.docs.hex-rays.com"
    l_links["developer_guide"] =                    "https://docs.hex-rays.com/developer-guide"
    l_links["getting_started_with_idapython"] =     "https://docs.hex-rays.com/developer-guide/idapython/idapython-getting-started"
    l_links["idapython_examples"] =                 "https://docs.hex-rays.com/developer-guide/idapython/idapython-examples"
    l_links["porting_guide"] =                      "https://docs.hex-rays.com/developer-guide/idapython/idapython-porting-guide-ida-9"
    l_links["HexRays_official_Youtube_channel"] =   "https://www.youtube.com/@HexRaysSA"
    l_links["AllThingsIDA_Youtube_channel"] =       "https://www.youtube.com/@allthingsida"
    l_links["AllThingsIDA_github"] =                "https://github.com/allthingsida/allthingsida"
    l_links["HexRays_official_plugins_repository"] ="https://plugins.hex-rays.com/"
    l_links["how_to_create_a_plugin"] =             "https://docs.hex-rays.com/developer-guide/idapython/how-to-create-a-plugin"
    l_links["appcall_guide"] =                      "https://docs.hex-rays.com/user-guide/debugger/debugger-tutorials/appcall_primer"
    l_links["appcall_practical_examples"] =         "https://hex-rays.com/blog/practical-appcall-examples/"
    # l_links[""] =  ""

    l_batch_mode = {}
    l_batch_mode["command_line"] = r"<full_path_to>ida.exe -A -S<script_I_want_to_run.py> -L<full_path_to>ida.log <full_path_to_input_file>"
    l_batch_mode["official_link"] = "https://docs.hex-rays.com/user-guide/configuration/command-line-switches"

    res = {}
    res["links"] = l_links
    res["abbreviations"] = l_abbreviations
    res["batch_mode"] = l_batch_mode

    if arg_open_browser_at_official_python_docs:
        _ida_kernwin.open_url(l_links["official_python_documentation"])

    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def open_url(arg_text_blob_with_urls_in_it_or_function: Union[str, Callable]) -> None:
    ''' Opens the default web brower with all URLs in the given text blob.
        Works well on the docstrings I have enriched with URLs: open_url(ida_kernwin.process_ui_action)

        Read more:

        Replacement for ida_kernwin.open_url()
    '''

    if isinstance(arg_text_blob_with_urls_in_it_or_function, str):
        l_url_regex: str = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))" # https://www.geeksforgeeks.org/python-check-url-string/
        urls = re.findall(l_url_regex, arg_text_blob_with_urls_in_it_or_function)
        if not urls:
            log_print(f"No URLs found in '{arg_text_blob_with_urls_in_it_or_function}'")
        for url in urls:
            _ida_kernwin.open_url(url[0])
        return

    # Check the docstring
    open_url(getattr(arg_text_blob_with_urls_in_it_or_function, "__doc__", ""))

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def bug_report(arg_bug_description: str, arg_module_to_blame: Union[str, ModuleType, None] = None) -> str:
    ''' If you find a bug in IDA or community_base (or any other plugin) you can easy save info about the bug by using this function.
    It will save what file you have open, the version of IDA pro, version of community_base and the bug description
    Will write a JSON file in the same directory as the IDB

    @param arg_bug_description A long description of the bug. Preferably on how to reproduce it.
    @param arg_module_to_blame The name of the module that is buggy, usually it's the plugin name or "IDA Pro"

    @return The full path to the bug report.
    '''
    l_timestamp: str = time.strftime("%Y_%m_%d_%H_%M_%S", datetime.datetime.timetuple(datetime.datetime.now()))
    l_bug_report_file: str = f"{input_file.idb_path}.{l_timestamp}.bug_report.json"
    l_bug_report: Dict[str, str] = {}
    l_bug_report["bug_in_module"] = _python_module_to_str(arg_module_to_blame)
    l_bug_report["IDA_version"] = str(ida_version())
    l_bug_report["decompiler_version"] = ida_decompiler_version()
    l_bug_report["community_base_version"] = __version__
    l_bug_report["python_version"] = str(python_version()[0]) + "." + str(python_version()[1]) # Tuple[major: int, minor: int] --> "3.12"
    l_bug_report["datetime"] = _timestamped_line("").strip()
    for key, value in input_file._as_dict().items():
        l_bug_report["input_file_" + key] = value
    l_bug_report["bug_description"] = arg_bug_description

    with open(l_bug_report_file, "w", encoding="UTF-8", newline="\n") as f:
        f.write(json.dumps(l_bug_report, ensure_ascii=False, indent=4, default=str))

    log_print(f"Wrote bug report in {l_bug_report_file}", arg_type="INFO")
    log_print("Please post this bug report to the creator of the module so they can fix it. Thank you!", arg_type="INFO")

    l_github_issues: str = __url__ + "/issues/new"
    # First argument is the default button that will be pressed if the user press ENTER as soon as the box popups
    if _ida_kernwin.ask_yn(_ida_kernwin.ASKBTN_YES , f"Open a new issue on Github? ( {l_github_issues} )") == _ida_kernwin.ASKBTN_YES:
        _ida_kernwin.open_url(l_github_issues)

    return l_bug_report_file

# TODO: This is not working as expected since it runs in it's own thread
class _check_if_long_running_script_should_abort_not_working():
    ''' Periodically check if any of the strings "abort.ida", "ida.abort", "ida.stop", "stop.ida" are in the clipboard. If anyone is, then throw an exception to abort the long running task.
    This is also an example on how to use timers. Read more: <https://github.com/HexRaysSA/IDAPython/blob/9.0sp1/examples/ui/register_timer.py>
    '''
    def __init__(self):
        l_time_between_calls_in_milliseconds = 1000
        self.interval = l_time_between_calls_in_milliseconds
        self.obj = _ida_kernwin.register_timer(self.interval, self)
        if self.obj is None:
            raise RuntimeError("Failed to register timer")
        self.times = 30

    def __call__(self):
        ''' This is the function that is invoked at each call '''
        # print("Timer invoked. %d time(s) left" % self.times)
        self.times -= 1
        # Unregister the timer when the counter reaches zero
        # return -1 --> do not call again, anything else

        clipboard = QApplication.clipboard()
        res = clipboard.text().strip() in ["abort.ida", "ida.abort", "ida.stop", "stop.ida"]
        if res:
            log_print(f"String {clipboard.text().strip()} found in clipboard")
            reload_module()

        return -1 if self.times == 0 else self.interval

    def __del__(self):
        ''' Clean up '''
        log_print(f"Timer object disposed {self}")

_g_timestamp_of_last_checked = time.time()
@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _check_if_long_running_script_should_abort(arg_debug: bool = False) -> None:
    ''' Scripts that take long time to run can be aborted by copying any of the following strings into the clipboard: "abort.ida", "ida.abort", "ida.stop", "stop.ida"
        This is checked every 30 seconds and raises a TimeoutError() exception

        WARNING! If you have multiple instances of IDA running with this script then the string check will be done in all instances and abort all long running scripts!
    '''
    # TODO: Add the possibility to add a PID in the string to just abort the correct script? Add if ever needed
    # TODO: Ask (with a popup) the user if this is the correct IDA to abort?
    global _g_timestamp_of_last_checked
    l_now = time.time()
    if (l_now - _g_timestamp_of_last_checked) > 30:
        _g_timestamp_of_last_checked = l_now
        if arg_debug:
            l_timestamp: str = time.strftime("%Y-%m-%d %H:%M:%S", datetime.datetime.timetuple(datetime.datetime.now()))
            print(f"{l_timestamp} _long_running_script_should_abort(): Checking for abort.ida in clipboard...")
        clipboard = QApplication.clipboard()
        res = clipboard.text().strip() in ["abort.ida", "ida.abort", "ida.stop", "stop.ida"]
        if res:
            raise TimeoutError(f"String {clipboard.text().strip()} found in clipboard")

    return

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _dict_sort(arg_dict: dict, arg_sort_by_value: bool = False, arg_descending: bool = False) -> dict:
    ''' Internal function. Returns a new sorted dictionary, can sort by value and can sort ascending or descending '''
    res = {}
    if arg_sort_by_value:
        res = dict(sorted(arg_dict.items(), key=lambda item: item[1])) # Sort by value ( lower -> higher )
    else:
        _list = sorted(arg_dict.items())
        for _t in _list:
            res[_t[0]] = _t[1]

    if arg_descending:
        res = {k: res[k] for k in reversed(res)} # Just reverse the dict
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _int_to_str_dict_from_module(arg_module: Union[ModuleType, str], arg_regexp: str) -> Dict[int, str]:
    ''' Internal function. Used to build dict from module enums.
        e.g. _int_to_str_dict_from_module(ida_ua, 'o_.*')
    '''
    l_module: ModuleType = sys.modules[arg_module] if isinstance(arg_module, str) else arg_module
    return {getattr(l_module, key): key for key in dir(l_module) if re.fullmatch(arg_regexp, key)}

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _dict_swap_key_and_value(arg_dict: dict) -> dict:
    ''' Internal function. Used with _int_to_str_dict_from_module to make dict that behaves as an enum.
        e.g.
        ofile_type_t = _int_to_str_dict_from_module("ida_loader", "OFILE_.*")
        ofile_type_t_enum = _dict_swap_key_and_value(ofile_type_t)
    '''
    res: dict = {}
    for k,v in arg_dict.items():
        res[v] = k
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def ida_version() -> int:
    ''' Returns the version of IDA currently running. 7.7 --> 770, 8.4 --> 840, 9.0 --> 900 '''
    return _ida_pro.IDA_SDK_VERSION

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def ida_user_dir() -> str:
    ''' Returns the path IDA is using as base when it looks for files
     Read more <https://hex-rays.com/blog/igors-tip-of-the-week-33-idas-user-directory-idausr>
    '''
    return _ida_diskio.get_user_idadir()

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def ida_plugin_dirs() -> List[str]:
    ''' Returns a list of directories where IDA looks for plugins
    For more info, see <https://hex-rays.com/blog/igors-tip-of-the-week-103-sharing-plugins-between-ida-installs>
    '''
    return _ida_diskio.get_ida_subdirs("plugins")

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def ida_is_running_in_batch_mode() -> bool:
    ''' Are we running in batch mode? a.k.a. headless
     OBS! I could not find a good way to check this so this is the best I could come up with
     Credits goes to Sark: <https://github.com/tmr232/Sark/blob/c57dd3571009fef5ae124155fe2bdf564e4d80d8/sark/qt.py#L50>
    '''
    return _ida_kernwin.get_current_widget() is None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def ida_save_and_exit(arg_exit_code: int = 0) -> None:
    ''' Save the IDB and clean exit IDA
    A good use for this function is as the last call in a script run in batch mode.
    See links() for more info about batch mode

    To exit without saving the IDB, see: <https://docs.hex-rays.com/developer-guide/idc/idc-api-reference/alphabetical-list-of-idc-functions/197>
    and <https://hex-rays.com/blog/igors-tip-of-the-week-116-ida-startup-files>

    process_config_directive(): <https://python.docs.hex-rays.com/namespaceida__idp.html#a8f7be5936a3a9e1f1f2bc7e406654f38>
    '''
    _ida_pro.qexit(arg_exit_code)
    return # We will never reach this line

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_get_ida_notepad_text() -> str:
    ''' Wrapper around ida_nalt.get_ida_notepad_text() that actually honors the type hints
    Read more: <https://python.docs.hex-rays.com/namespaceida__nalt.html#afbce150733a7444c14e83db7411cf3c9>

    Tag: Community fix, IDA Bug
    '''
    return _ida_nalt.get_ida_notepad_text() or ""

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def notepad_text(arg_text: Optional[str] = None, arg_debug: bool = False) -> str:
    ''' IDA has a text field that the user can write whatever they want in.
    This function can read and write this text field. '''
    # TODO: The max size seems to be 0x101c00 (just over 1MB), should I check for the length?
    if arg_text is not None:
        _ida_nalt.set_ida_notepad_text(str(arg_text))
    res = _idaapi_get_ida_notepad_text()
    log_print(f"ida_nalt.get_ida_notepad_text() returned {res}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def ida_decompiler_version() -> str:
    ''' What version of Hexrays decompiler we are running '''
    l_arch = f"{input_file.format}, {input_file.bits} bits, {input_file.endian} endian"
    l_error_str: str = f"<<< No decompiler for {l_arch} is loaded >>>"
    if not _ida_hexrays.init_hexrays_plugin():
        log_print(l_error_str, arg_type="ERROR")
        return l_error_str
    l_temp: Optional[str] = _ida_hexrays.get_hexrays_version()
    if l_temp is None:
        log_print(l_error_str, arg_type="ERROR")
        return l_error_str
    return l_temp

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def python_version() -> Tuple[int, int]:
    ''' Find the Python version we are running.
    Returns a tuple with (major_version: int, minor_version: int)
    '''
    return (sys.version_info.major, sys.version_info.minor)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _python_module_to_str(arg_module: Union[str, ModuleType, None] = None) -> str:
    ''' Internal function. Get a Python module name from the argument. If argument is None, then return the module name of ourself '''
    # TODO: Should I verify that arg_module actually is a module?
    return arg_module if isinstance(arg_module, str) else getattr(arg_module, '__name__', __name__)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def reload_module(arg_module: Union[str, ModuleType, None] = None) -> bool:
    '''  During development, it's nice to have an easy way to reload the file and update all changes
    Read more: <https://hex-rays.com/blog/loading-your-own-modules-from-your-idapython-scripts-with-idaapi-require>

    @param arg_module if this is set to None, then reload ourself

    @return Returns True if we reloaded successful, False otherwise

    Replacement for ida_idaapi.require()
    '''
    l_module_name: str = _python_module_to_str(arg_module)
    log_print(f"Reloading '{l_module_name}' ( {getattr(sys.modules.get(l_module_name, ''), '__file__', '<<< no file found >>>')} ) using ida_idaapi.require('{l_module_name}')", arg_type="INFO")
    try:
        _ida_idaapi.require(l_module_name)
        res = True
    except ModuleNotFoundError as exc:
        log_print(f"Could NOT reload {l_module_name}, exception: {exc}", arg_type="ERROR")
        res = False
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _timestamped_line(arg_str: str) -> str:
    ''' Add a timestamp at the beginning of the line
     e.g. 2024-12-31 13:59:59 This is the string I send in as argument
    '''
    return time.strftime("%Y-%m-%d %H:%M:%S", datetime.datetime.timetuple(datetime.datetime.now())) + " " + arg_str

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _file_and_line_number(arg_num_function_away: int = 2) -> Optional[_inspect.Traceback]:
    ''' Internal function. Used in log_print()
    Returns the file the script is called from and what line in that script file

    ! WARNING ! This function is VERY expensive!
    '''
    try:
        callerframerecord = _inspect.stack()[arg_num_function_away]     # 0 represents this line
        frame = callerframerecord[0]                                    # 1 represents line at caller and so on
        return _inspect.getframeinfo(frame)                              # info.filename, info.function, info.lineno
    except Exception as exc:
        print(_timestamped_line(f"Caught exception: {exc}"))
        return None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def log_print(arg_string: str, arg_actually_print: bool = True, arg_type: str = "DEBUG", arg_num_function_away: int = 6) -> None:
    ''' Used for code trace while developing the project '''
    _check_if_long_running_script_should_abort(arg_actually_print)
    if arg_actually_print or __GLOBAL_LOG_EVERYTHING:
        info = _file_and_line_number(arg_num_function_away)
        if info is None:
            print(_timestamped_line("_file_and_line_number failed"))
            return
        function_name: str = info.function if info else "<no function name>"
        if function_name == "<module>":
            function_name = os.path.basename(info.filename)
        else:
            function_name = f"{os.path.splitext(os.path.basename(info.filename))[0]}.{function_name}"
        log_line = _timestamped_line(f"[{arg_type}] {function_name}:{info.lineno} --> {arg_string}")

        # Log to disk can be implemented here if needed
        print(log_line, flush=True)
    return

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def ida_is_64bit() -> bool:
    ''' Is the IDA process you are running in a 64 bit process? '''
    return _ida_idaapi.__EA64__

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _ida_DLL() -> Union[ctypes.CDLL, ctypes.WinDLL]:
    ''' Load correct version of ida.dll. Work on IDA 8.4 and 9.0. Example of how to use ctypes. '''

    l_bits: str = "64" if ida_is_64bit() else "32"
    if ida_version() >= 900:
        l_bits = "" # IDA 9.0 removed the ida64.dll and ida32.dll and just calls it ida.dll now

    if sys.platform == 'win32':
        res = ctypes.windll[f'ida{l_bits}.dll'] # windll is STDCALL
    elif 'linux' in sys.platform.lower():
        res = ctypes.cdll[f'libida{l_bits}.so']  # cdll is CDECL
    elif sys.platform == 'darwin':
        res = ctypes.cdll[f'libida{l_bits}.dylib'] # Not tested, cdll is CDECL
    else:
        log_print(f"You are using an OS I do not know: {sys.platform}", arg_type="ERROR")
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _loader_name() -> str:
    ''' Internal function. Example of how to use ctypes to call IDA C api.
    Read more: <https://hex-rays.com/blog/calling-ida-apis-from-idapython-with-ctypes>
    get_loader_name: <https://cpp.docs.hex-rays.com/loader_8hpp.html#a9c79e47be0a36e47363409f3ce9ce6c5>
    '''
    l_IDA_dll = _ida_DLL()
    l_buf_size: int = 256
    l_buf = ctypes.create_string_buffer(l_buf_size)
    l_exported_function_name = 'get_loader_name'
    l_IDA_dll[l_exported_function_name].argtypes = ctypes.c_char_p, ctypes.c_size_t
    l_IDA_dll[l_exported_function_name].restype = ctypes.c_size_t
    l_IDA_dll[l_exported_function_name](l_buf, l_buf_size) # This is the weird way ctypes calls functions
    return l_buf.value.decode('utf-8') # buf.raw gives the whole buffer

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def hex_dump(arg_ea: Union[EvaluateType, bytes, bytearray], arg_len: Optional[EvaluateType] = None, arg_width: int = 0x10, arg_unprintable_char: str = '.', arg_debug: bool = False) -> None:
    ''' Prints the given data as <address> <byte value> <text> in the same style as IDAs hex view does. '''

    l_addr: int = 0
    if isinstance(arg_ea, (bytes, bytearray)):
        l_len: Optional[int] = len(arg_ea) if arg_len is None else eval_expression(arg_len, arg_debug=arg_debug)
        if l_len is None:
            log_print(f'eval_expression({arg_len}) failed')
            return
        l_bytes: bytes = bytes(arg_ea[0:l_len])
    else:
        l_addr = address(arg_ea, arg_debug=arg_debug)
        if l_addr == _ida_idaapi.BADADDR:
            log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
            return

        l_len = 0x10 if arg_len is None else eval_expression(arg_len, arg_debug=arg_debug)
        if l_len is None:
            log_print(f'eval_expression({arg_len}) failed', arg_type="ERROR")
            return
        l_bytes_temp = read_bytes(arg_ea=l_addr, arg_len=l_len, arg_debug=arg_debug)
        if l_bytes_temp is None:
            log_print(f'read_bytes({_hex_str_if_int(arg_ea)}) failed', arg_type="ERROR")
            return
        l_bytes = l_bytes_temp

    l_temp: List[str] = []
    digits: int = 2

    l_len = len(l_bytes) if l_bytes is not None else 0x10
    for buf_offset in range(0, l_len, arg_width):
        s = l_bytes[buf_offset:buf_offset + arg_width]
        hexa = ' '.join(["%0*X" % (digits, x) for x in s]) # TODO: Make more readable...
        hexa = hexa.ljust(arg_width * (digits + 1), ' ')
        text = ''.join([chr(x) if 0x20 <= x < 0x7F else arg_unprintable_char for x in s])
        l_temp.append(f"{l_addr+buf_offset:08X}  {hexa}   {text}")

    print('\n'.join(l_temp))
    _ida_kernwin.request_refresh(_ida_kernwin.IWID_ALL)
    return

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def hex_parse(arg_list_of_strs: BufferType, arg_debug: bool = False) -> List[str]:
    ''' Parse data that can be very messed up as good as I can
    @return List[hex_as_text: str]

    e.g.
    hex_parse('aa bb cc') --> ['aa', 'bb', 'cc']
    '''
    if not arg_list_of_strs: # ida_nalt.retrieve_input_file_crc32() for some reason return 0 when no file is loaded, ida_nalt.retrieve_input_file_md5() returns None
        return []

    l_list_of_inputs = [arg_list_of_strs] if isinstance(arg_list_of_strs, (str, bytes, bytearray)) else arg_list_of_strs
    l_list_of_strs: List[str] = []
    if isinstance(l_list_of_inputs[0], (bytes, bytearray)):
        for line in l_list_of_inputs:
            hex_line: str = ""
            for b in line:
                hex_line += f"{b:02x}"
            l_list_of_strs.append(hex_line)
    else:
        l_list_of_strs = l_list_of_inputs # type: ignore[assignment] # I think this is correct bu mypy does not like it

    log_print(f'l_list_of_strs is now: {l_list_of_strs}', arg_debug)

    res: List[str] = []
    hex_byte: str = "[0-9A-F][0-9A-F]"
    beginning_of_line: str = hex_byte + hex_byte + hex_byte + r" \s*?((?:" + hex_byte + "(?:[ -]{1,3}|$))+)"

    for line in l_list_of_strs:
        line = line.strip()
        if not line:
            continue

        m = re.findall(beginning_of_line, line, re.IGNORECASE)
        if len(m) == 0: # There is no "extra output from the host program" so we just parse the hex raw
            hex_data = re.findall(hex_byte, line, re.IGNORECASE)
        else:
            hex_data = re.split(" |-", m[0].strip())

        for i in hex_data:
            if len(i):
                res.append(i)

    if not res:
        res = []
        log_print("Result is empty. Your input might be wrong?", arg_type="ERROR")

    log_print(f'res: {res}', arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _signed_hex_text(arg_expression: EvaluateType, arg_nbits: int = 0, arg_debug: bool = False) -> Optional[str]:
    ''' Easy way to get nice formatting on signed values.
        @param arg_nbits: The bit width of the variable. Since Python has no fixed bit width int types, you have to specify this. If you don't specify it, I assume it's the input_file.bits width
    '''
    l_nbits = arg_nbits if arg_nbits else input_file.bits
    l_value: Optional[int] = eval_expression(arg_expression=arg_expression, arg_debug=arg_debug)
    if l_value is None:
        log_print(f"'{arg_expression}' failed in eval_expression", arg_type="ERROR")
        return None
    res = hex(_ida_idaapi.as_signed(l_value, nbits=l_nbits))
    if not res.startswith('-'):
        res = '+' + res
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _operand_parser(arg_operand: _ida_ua.op_t, arg_debug: bool = False) -> Optional[dict]:
    ''' Internal function. Split the operand into a dict with info about the parts of the operand '''
    res = {}
    if arg_operand.type == _ida_ua.o_void:
        pass # I don't like this code but IDA use invalid operands with the type o_void to say that this is an invalid operand
    elif arg_operand.type == _ida_ua.o_reg:
        l_reg_name = _ida_idp.get_reg_name(arg_operand.reg, _data_type_sizes[arg_operand.dtype])
        l_reg_name = l_reg_name.replace('$','').lower() # MIPS...
        l_register = registers._as_dict[l_reg_name.lower()]
        res['register'] = l_register
    elif arg_operand.type in [_ida_ua.o_mem, _ida_ua.o_far, _ida_ua.o_near]:
        res['address'] = arg_operand.addr
    elif arg_operand.type in [_ida_ua.o_phrase, _ida_ua.o_displ]:
        if input_file.processor != 'metapc':
            log_print("This only works for Intel x86 and x64.", arg_type="ERROR")
            return None

        # specflag1 and specflag2 are not really documented. Use this code at own risk.
        if arg_operand.specflag1 == 0:
            log_print("specflag1 == 0", arg_debug)
            l_base_reg: str = _ida_idp.get_reg_name(arg_operand.reg, input_file.bits // 8)
            l_base_reg = l_base_reg.replace('$', '').lower() # MIPS
            res['base_register'] = registers._as_dict[l_base_reg]
            res['displacement'] = arg_operand.addr
        elif arg_operand.specflag1 == 1:
            log_print("specflag1 == 1.", arg_debug)
            log_print(f"specflag2: {bin(arg_operand.specflag2)}.", arg_debug)
            l_scale = (arg_operand.specflag2 >> 6) & 0x03
            l_scale = 1 << l_scale if l_scale else 0 # The special case of 0 --> scale 0

            l_base_reg = _ida_idp.get_reg_name(arg_operand.specflag2 & 0x07, input_file.bits // 8)
            l_base_reg = l_base_reg.replace('$', '').lower() # MIPS
            l_index_reg: str = _ida_idp.get_reg_name((arg_operand.specflag2 >> 3) & 0x07, input_file.bits // 8)
            l_index_reg = l_index_reg.replace('$', '').lower() # MIPS

            res['base_register'] = registers._as_dict[l_base_reg]
            res['index_register'] = registers._as_dict[l_index_reg]
            res['scale'] = l_scale
            res['displacement'] = arg_operand.addr

    elif arg_operand.type == _ida_ua.o_imm:
        res['value'] = arg_operand.value
    elif arg_operand.type == _ida_ua.o_idpspec1:
        if input_file.processor == 'metapc':
            res['register'] = f"dr{arg_operand.reg}"
        return res
    elif arg_operand.type == _ida_ua.o_idpspec2:
        if input_file.processor == 'metapc':
            res['register'] = f"cr{arg_operand.reg}"
        return res
    else:
        l_operand_types = _int_to_str_dict_from_module('_ida_ua', 'o_.*')
        log_print(f"Unknown operand type, we got 0x{arg_operand.type:x}: {l_operand_types.get(arg_operand.type, '<unknown operand type>')} which I cannot handle.", arg_type="ERROR")
        return None
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _hex_str_if_int(arg_in: Any, arg_debug: bool = False) -> str:
    ''' If arg_in is an int, then return the string with the hex value, the decimal value and if the int is an valid address: the name of that address
    e.g. '0x400000 (4194304) name: main'

        If arg_in is NOT an int, then we return str(arg_in)
    '''
    if not isinstance(arg_in, int):
        return str(arg_in)

    res: str = f"0x{arg_in:x} ({arg_in})"
    if arg_in == _ida_idaapi.BADADDR:
        res = f"0x{_ida_idaapi.BADADDR:x} (ida_idaapi.BADADDR)"
    elif _ida_bytes.is_mapped(arg_in):
        res += f" name: {name(arg_in, arg_debug=arg_debug)}"
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def copy_hex_text_to_clipboard(arg_ea_start: EvaluateType = 0, arg_len: EvaluateType = 0, arg_debug: bool = False) -> None:
    ''' Selected bytes will be copied as hex text to the clipboard '''
    _ = dump_to_disk(arg_ea_start=arg_ea_start, arg_len=arg_len, arg_filename="|clipboard|", arg_debug=arg_debug) # "|clipboard|" --> We don't actually dump to disk
    return

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _whitespace_zapper(arg_in_string: str) -> str:
    ''' Internal function. If there are multiple spaces in a row in the input line, they are replaced by only 1 space. '''
    res = arg_in_string
    while res != res.replace('  ', ' '):
        res = res.replace('  ', ' ')
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _lnot(arg_expression: _ida_hexrays.cexpr_t) -> _ida_hexrays.cexpr_t:
    ''' Logical NOT of expression. See <https://github.com/tmr232/idapython/blob/0028bac2975e9cfd68ce39e908d1fc923e94000b/examples/vds3.py#L94>
    a cexpr_t with "x == y" will return "x != y"
    '''
    return _ida_hexrays.lnot(_ida_hexrays.cexpr_t(arg_expression))

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_retrieve_input_file_md5() -> bytes:
    ''' Wrapper around ida_nalt.retrieve_input_file_md5() but this we honor the type hints

    Tags: Community fix, IDA Bug
    '''
    return _ida_nalt.retrieve_input_file_md5() or bytes()

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_retrieve_input_file_sha256() -> bytes:
    ''' Wrapper around ida_nalt.retrieve_input_file_sha256() but we honor the type hints

    Tags: Community fix, IDA Bug
    '''
    l_temp: Optional[bytes] = _ida_nalt.retrieve_input_file_sha256()
    return l_temp or bytes()

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _pretty_print_size(arg_input_size: int) -> Optional[str]:
    ''' Convert a large number to the correct postfix (KB, MB, GB, TB)
    e.g. _pretty_print_size(1231231332) --> '1.15G'
    Read more: <https://cpp.docs.hex-rays.com/group__conv.html#gab6147a3e263d08eb2b9c2439b4653526>
    Example on how to use the C api from Python.
    '''

    l_IDA_dll = _ida_DLL()
    l_buf_size = 8 # Enough according to the official docs
    l_buf = ctypes.create_string_buffer(l_buf_size)
    l_exported_function_name = "pretty_print_size"
    l_IDA_dll[l_exported_function_name].argtypes = ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint64
    l_IDA_dll[l_exported_function_name].restype = ctypes.c_size_t
    l_IDA_dll[l_exported_function_name](l_buf, l_buf_size, arg_input_size)
    return l_buf.value.decode('utf-8') # buf.raw gives the whole buffer

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def google(arg_search: str) -> str:
    ''' Fast track to search '''
    l_search_engine_base: str = "https://www.google.com/search?q="
    res = l_search_engine_base + arg_search
    _ida_kernwin.open_url(res)
    return res

# API extension ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


class _input_file_object():
    ''' Information about the file that is loaded in IDA such as filename, file type and so on

        Please use the object created in community_base.input_file. E.g. print(community_base.input_file.idb_path)
    '''
    bits = property(fget=lambda self: 64 if _ida_ida.inf_is_64bit() else 32 if _ida_ida.inf_is_32bit_exactly() else 16, doc='64/32/16: int')
    crc32 = property(fget=lambda self: ''.join(hex_parse(_ida_nalt.retrieve_input_file_crc32().to_bytes(4, 'big'))), doc='CRC-32 as ascii string')
    endian = property(fget=lambda self: 'big' if _ida_ida.inf_is_be() else 'little' if self.filename else '<<< no file loaded >>>', doc='"big" or "little" (or "<<< no file loaded >>>" if no file is loaded)')
    entry_point = property(fget=lambda self: _ida_ida.inf_get_start_ip(), doc='Address of the first instruction that is executed')
    filename = property(fget=lambda self: _ida_nalt.get_input_file_path() or "", doc='Full path and filename to the file WHEN IT WAS LOADED INTO IDA. The file might been moved by the user and this path might not be valid.')
    format = property(fget=lambda self: _ida_loader.get_file_type_name() if self.filename else "<<< no file loaded >>>", doc='Basically PE or ELF. e.g. PE gives "Portable executable for 80386 (PE)"')
    # idb_creation_time = property(fget=lambda self: time.strftime("%Y-%m-%d %H:%M:%S", datetime.datetime.timetuple(datetime.datetime.fromtimestamp(_ida_nalt.get_idb_ctime()))), doc='When the IDB was created') # useless?
    # idb_opened_number_of_times = property(fget=lambda self: _ida_nalt.get_idb_nopens(), doc='Number of times the IDB have been opened') # useless?
    idb_path = property(fget=lambda self: _ida_loader.get_path(_ida_loader.PATH_TYPE_IDB), doc='Full path to the IDB. Replacement for ida_utils.GetIdbDir()')
    # idb_work_seconds = property(fget=lambda self: _ida_nalt.get_elapsed_secs(), doc='Number of seconds the IDB have been open') # useless?
    idb_version = property(fget=lambda self: _ida_ida.inf_get_version(), doc='The version that the IDB format is in. If you created the IDB in an older version of IDA Pro, then this will differ from ida_version()')
    imagebase = property(fget=lambda self: _ida_nalt.get_imagebase(), doc='The address the input file will be/is loaded at')
    is_dll = property(fget=lambda self: _ida_ida.inf_is_dll(), doc='Is the file a DLL file?')
    loader = property(fget=lambda self: _loader_name().upper() if self.filename else "<<< No file loaded >>>", doc='Name of the IDA loader that is parsing the file when loading it into IDA')
    min_ea = property(fget=lambda self: _ida_ida.inf_get_min_ea(), doc='Lowest Effective Address (EA) in the database. If the input file is started in a debugger, this value will be the lowest EA in the process.')
    max_ea = property(fget=lambda self: _ida_ida.inf_get_max_ea(), doc='Highest Effective Address (EA) in the database (but + 1). If the input file is started in a debugger, this value will be the higheest EA in the process.')
    min_original_ea = property(fget=lambda self: _ida_ida.inf_get_omin_ea(), doc='Lowest Effective Address (EA) in the database. If the input file is started in a debugger, this value will be the same as when the process is NOT started.')
    max_original_ea = property(fget=lambda self: _ida_ida.inf_get_omax_ea(), doc='Highest Effective Address (EA) in the database (but + 1). If the input file is started in a debugger, this value will be the same as when the process is NOT started')
    md5 = property(fget=lambda self: ''.join(hex_parse(_idaapi_retrieve_input_file_md5())), doc='MD5 as ascii string')
    processor = property(fget=lambda self: _ida_ida.inf_get_procname(), doc='IDAs name for the processor. E.g. "metapc" for Intel x64 assembly, "ARM" for ARM 32')
    size = property(fget=lambda self: _ida_nalt.retrieve_input_file_size(), doc='The target file size in bytes. _NOT_ the IDB size.')
    sha256 = property(fget=lambda self: ''.join(hex_parse(_idaapi_retrieve_input_file_sha256())), doc='SHA-256 as ascii string')

    def _as_dict(self) -> Dict[str, str]:
        ''' Return all info about the file in a dict (JSON) '''
        res = {}
        for l_property in dir(self):
            if l_property.startswith('_'):
                continue
            l_property_value = getattr(self, l_property)
            if isinstance(l_property_value, int) and not l_property in ['bits', 'idb_version', 'is_dll', 'idb_work_seconds', 'idb_opened_number_of_times']:
                l_property_value = f"0x{l_property_value:x}"
            else:
                l_property_value = str(l_property_value)
            res[l_property] = l_property_value
        return res

    def __str__(self):
        ''' Print all the properties as string '''
        res = ""
        for k,v in self._as_dict().items():
            res += f"{k}: {v}\n"
        return res

    def __repr__(self):
        return f"{type(self)} which has str(self):\n{str(self)}"

input_file = _input_file_object() # Recreated in the "new_file_opened_notification_callback" function

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def current_address() -> int:
    ''' Returns the address where cursor is. (OBS! Cursor in IDA is NOT the mouse cursor but where the blinking line is)
    Replacement for ida_kernwin.get_screen_ea()
    '''
    return _ida_kernwin.get_screen_ea()

here = current_address

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_str2ea(arg_expression: str, arg_screen_ea: int = _ida_idaapi.BADADDR) -> int:
    '''  wrapper around ida_kernwin.str2ea() (without the exception)
    IDA < 8.3: _ida_kernwin.str2ea returns BADADDR, IDA >= 8.3: returns None

    @return Returns ida_idaapi.BADADDR on failure

    Read more: <https://python.docs.hex-rays.com/namespaceida__kernwin.html#a08d928125a472cc31098defe54be7382>

    Tag: Community fix
    '''
    try:
        l_ida_kernwin_str2ea_res: Optional[int] = _ida_kernwin.str2ea(arg_expression, arg_screen_ea)
        res = l_ida_kernwin_str2ea_res if l_ida_kernwin_str2ea_res is not None else _ida_idaapi.BADADDR
    except TypeError as exc:
        log_print(f'ida_kernwin.str2ea("{arg_expression}") failed. Exception: {exc}', arg_type="ERROR")
        res = _ida_idaapi.BADADDR
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def eval_expression(arg_expression: EvaluateType, arg_supress_error: bool = False, arg_debug: bool = False) -> Optional[int]:
    ''' This function tries to evaluate whatever you give it into an int. E.g. "esi + edx * 0x10 + 3" (if the debugger is running) or "0x11 + 0x11"

        Replacement for ida_kernwin.str2ea()

        OBS! This is NOT a pure replacement of ida_kernwin.str2ea()!
        ida_kernwin.str2ea("11") --> 0x11, eval_expression("11") --> 0x0B

        @return Returns the value (int) that the the input evaluated to
    '''
    if isinstance(arg_expression, int): # Can handle an address in int form i.e. ea_t
        log_print(f"arg_expression is of type int: 0x{arg_expression:x} ({arg_expression})", arg_debug)
        return arg_expression

    if isinstance(arg_expression, _ida_ua.op_t):
        log_print(f"arg_expression is a {type(arg_expression)} with sub type: {_operand_type[arg_expression.type]} which I can handle", arg_debug)
        if arg_expression.type in [_ida_ua.o_mem, _ida_ua.o_near, _ida_ua.o_far]:
            return arg_expression.addr

        if arg_expression.type in [_ida_ua.o_imm]:
            return arg_expression.value64 or arg_expression.value

        log_print(f"arg_expression is of type {type(arg_expression)} with sub type: {_operand_type[arg_expression.type]} which can NOT be converted into an int", arg_type="ERROR")
        return None

    if isinstance(arg_expression, _ida_typeinf.funcarg_t) and arg_expression.argloc.is_reg1():
        log_print(f"arg_expression is a {type(arg_expression)} with argloc == ALOC_REG1 which I can handle", arg_debug)
        return _register(arg_expression.register,arg_debug=arg_debug)

    if isinstance(arg_expression, _ida_idp.reg_info_t):
        log_print(f"arg_expression is a {type(arg_expression)} which I can handle", arg_debug)
        arg_expression = _register(arg_expression, arg_debug=arg_debug)
        return arg_expression

    if isinstance(arg_expression, _ida_hexrays.carg_t):
        log_print(f"arg_expression is a {type(arg_expression)} which I can handle", arg_debug)
        return arg_expression.ea

    known_address_attributes = ['ea',       # _ida_ua.insn_t, _ida_hexrays.cinsn_t, _ida_hexrays.cexpr_t
                                'start_ea', # _ida_hexrays.cfuncptr_t, _ida_segment.segment_t, _ida_range.range_t
                                'entry_ea', # _ida_funcs.func_t
                                'value',    # _ida_idaapi.PyIdc_cvt_int64__ (from appcalls in x64)
                                'defea',    # _ida_hexrays.lvar_t
                                'base'      # _ida_idd.modinfo_t
                               ]

    for attribute in known_address_attributes:
        if hasattr(arg_expression, attribute):
            log_print(f"arg_expression is of type: {type(arg_expression)} which has an attribute called '{attribute}' which is what I use", arg_debug)
            return getattr(arg_expression, attribute)

    if not isinstance(arg_expression, str):
        if arg_debug or not arg_supress_error:
            log_print(f"arg_expression cannot be parsed in any meaningful way. You gave me {type(arg_expression)}", arg_type="ERROR")
        return None

    if arg_expression.lower() in ('here', 'cursor'):
        return current_address()

    if arg_expression.lower() == 'peb':
        return win_PEB(arg_debug=arg_debug)

    arg_expression = arg_expression.replace("`", "") # Handle WinDBGs funky address string.
    if arg_expression.startswith(('-', '+')): # ida_kernwin.str2ea() behaves strange when the first character is either - or +
        l_sign: str = arg_expression[0]
        log_print(f"calling eval_expression() recursive with '{arg_expression[1:]}'", arg_debug)
        res = eval_expression(arg_expression[1:], arg_debug=arg_debug)
        if res is None:
            log_print("recursive eval_expression() returned None", arg_type="ERROR")
            return None
        return res if l_sign == '+' else -res

    debugger_refresh_memory_WARNING_VERY_EXPENSIVE()
    if re.fullmatch(r"^\d+$", arg_expression): # This regexp just means "all digits"
        arg_expression = arg_expression + "." # Transfor a number in string format (e.g. "22") --> "22." (parse as 22 in decimal and NOT in hex) This is done so eval_expression("11") == eval_expression("0+11"). ida_kernwin.str2ea("11") != ida_kernwin.str2ea("0+11")

    res = _idaapi_str2ea(arg_expression) # Is it a simple expression? This can handle register name as string
    if res == _ida_idaapi.BADADDR:
        res = _idaapi_str2ea(f"kernel32_{arg_expression}") # Simplify kernel32 API lookups e.g. GetProcAddress --> kernel32_GetProcAddress
        log_print(f"KERNEL32 API lookup: ida_kernwin.str2ea('kernel32_{arg_expression}') resolved to 0x{res:x}", arg_debug)
        if res != _ida_idaapi.BADADDR:
            return res
    else:
        log_print(f"Simple expression eval: ida_kernwin.str2ea('{arg_expression}') resolved to 0x{res:x}", arg_debug)
        return res

    # Try to regexp out something out of the strange string the user gave me
    l_regexp_label_and_address = "[0-9a-f]{4,16}|(?:[a-z_?][a-z_?0-9@$]+)" # IDA does allow you to use ':' in the name BUT it will be printed as '_' so to avoid confusion, I do NOT allow ':' nor '.'
    matches = re.findall(l_regexp_label_and_address, arg_expression, re.IGNORECASE)

    log_print("Following matches will be tested as a destination:", arg_debug)
    log_print(str(matches), arg_debug)

    # The following code snippet can parse a longer line and try to take out tokens that can be a name or address.
    # E.g. "This line has some strange prefix .text:000000018001EB2A                 mov     rdi, rax" --> 0x000000018001EB2A
    for match in matches: # Return the first match that can be parsed as an int
        try:
            res = _idaapi_str2ea(match)
            log_print(f"_ida_kernwin.str2ea('{match}') resolved to 0x{res:x}", arg_debug)

            if res == _ida_idaapi.BADADDR:
                if match[0:1].lower() == 'x':
                    match = match[1:]
                res = int(match, 16)
            return res
        except:
            pass

    if arg_debug or not arg_supress_error:
        log_print(f"arg_expression cannot be parsed in any meaningful way. You gave me {type(arg_expression)}", arg_type="ERROR")
    return None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def address(arg_label_or_address: EvaluateType, arg_supress_error: bool = False, arg_debug: bool = False) -> int:
    ''' Takes a name/label or register name (if the debugger is active)
    or address (int) and try to resolve it into an address (int) in a smart way.
    You can use the syntax +<num bytes> and -<num bytes> to jump down or up from the current_address()
    @return Returns a valid address (int) on success and ida_idaapi.BADADDR on fail
    Replacement for ida_name.get_name_ea()
    '''
    # Resolve cursor relative jmps such as "+0x10" meaning current_address() + 0x10
    if isinstance(arg_label_or_address, int):
        res: Optional[int] = arg_label_or_address
    elif isinstance(arg_label_or_address, str) and arg_label_or_address.startswith("+"):
        res = current_address() + eval_expression(arg_label_or_address[1:], arg_debug=arg_debug) # type: ignore
    elif isinstance(arg_label_or_address, str) and arg_label_or_address.startswith("-"):
        res = current_address() - eval_expression(arg_label_or_address[1:], arg_debug=arg_debug) # type: ignore
    else:
        res = eval_expression(arg_label_or_address, arg_supress_error=arg_supress_error, arg_debug=arg_debug)

    if res is None or not _ida_bytes.is_mapped(res):
        return _ida_idaapi.BADADDR

    log_print(f"arg_label_or_address resolved to 0x{res:x}", arg_debug) # WARNING! Do NOT evalutate the arg_label_or_address variable in the string, this cause circular references
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def relative_virtual_address(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[int]:
    ''' Returns the offset from imagebase to the given address a.k.a RVA '''
    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None
    return l_addr - input_file.imagebase

rva = relative_virtual_address

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def function(arg_ea: EvaluateType,
             arg_create_function: bool = False,
             arg_debug: bool = False) -> Optional[_ida_funcs.func_t]:
    ''' Get a function object (ida_funcs.func_t) at given address.

    Replacement for ida_funcs.get_func() and ida_funcs.add_func() '''

    if isinstance(arg_ea, _ida_funcs.func_t):
        log_print("arg_ea is already of type _ida_funcs.func_t.", arg_debug, arg_type="WARNING")
        return arg_ea

    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    if arg_create_function or is_unknown(l_addr, arg_debug=arg_debug):
        make_code(l_addr, arg_debug=arg_debug)
        _ida_funcs.add_func(l_addr)

    _ida_auto.auto_wait()
    if not is_code(l_addr, arg_debug=arg_debug):
        log_print(f"The address: 0x{l_addr:x} is not marked as code. You can force this by adding arg_create_function=True in the arguments", arg_type="ERROR")
        return None

    res: Optional[_ida_funcs.func_t] = _ida_funcs.get_func(l_addr)
    if not res:
        log_print(f"_ida_funcs.get_func(0x{l_addr:x}) returned None.", arg_debug, arg_type="ERROR")
        return None

    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _is_lumina_name(arg_function: EvaluateType, arg_debug: bool = False) -> Optional[bool]:
    l_func = function(arg_function, arg_debug=arg_debug)
    if l_func is None:
        log_print(f"Could not locate any function at {_hex_str_if_int(arg_function)}", arg_type="ERROR")
        return None
    return bool(l_func.flags & _ida_funcs.FUNC_LUMINA)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def decompile(arg_ea: EvaluateType,
              arg_hf: Optional[_ida_hexrays.hexrays_failure_t] = None,
              arg_flags: int = _ida_hexrays.DECOMP_GXREFS_DEFLT,
              arg_create_function: bool = False,
              arg_force_fresh_decompilation: bool = True,
              arg_debug: bool = False
              ) -> Optional[_ida_hexrays.cfuncptr_t]:
    ''' The problem with the normal ida_hexrays.decompile() is that it's not done with the decompilation when the the function returns.
    You can see the difference if you run: cfunc = ida_hexrays.decompile(<function that has not been decompiled before>);print(f"len of treeitems: {len(cfunc.treeitems)}")

    @param arg_flags Default is ida_hexrays.DECOMP_GXREFS_DEFLT. Read more: <https://python.docs.hex-rays.com/namespaceida__hexrays.html#a25116e19a146df6d38b7c8cdb265e621>

    Replacement for ida_hexrays.decompile()

    If you want to decompile many functions and save the result into a file, then use the function decompile_many()
    '''
    if not _ida_hexrays.init_hexrays_plugin():
        l_arch = f"{input_file.format}, {input_file.bits} bits, {input_file.endian} endian"
        log_print(f"The decompiler for this architecture ({l_arch}) is not loaded.", arg_debug, arg_type="ERROR")
        return None # Since the user will get many warning about it not being loaded when starting IDA pro, I suppress the log message unless the user explicitly asks for it

    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    l_func = function(l_addr, arg_create_function=arg_create_function, arg_debug=arg_debug)
    if not l_func:
        log_print(f"Could not create a function at {_hex_str_if_int(arg_ea)}", arg_debug, arg_type="ERROR")
        return None
    l_function_address: int = address(l_func, arg_debug=arg_debug)

    if arg_force_fresh_decompilation:
        log_print(f"arg_force_fresh_decompilation set so we call ida_hexrays.mark_cfunc_dirty(0x{l_function_address:x})", arg_debug)
        _ida_hexrays.mark_cfunc_dirty(l_function_address)

    try:
        l_cfunc = _ida_hexrays.decompile(ea=l_function_address, hf=arg_hf, flags=arg_flags) # This will _NOT_ populate the l_cfunc.treeitems
        l_cfunc.get_pseudocode()                                  # Forces the l_cfunc.treeitems to be populated
        return l_cfunc
    except Exception as exc:
        log_print(f"0x{l_function_address:x} failed to decompile", arg_debug, arg_type="ERROR")
        log_print(str(exc), arg_debug, arg_type="ERROR")
        return None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def decompile_many(arg_outfile: str = input_file.idb_path + '.c',
                   arg_functions: Optional[List[EvaluateType]] = None,
                   arg_flags: int = _ida_hexrays.VDRUN_MAYSTOP,
                   arg_debug: bool = False) -> bool:
    '''Decompile many (all) functions to a file on disk
       Replacement for ida_hexrays.decompile_many()

       @param arg_flags: int Default is ida_hexrays.VDRUN_MAYSTOP which means that the user can cancel decompilation. <https://python.docs.hex-rays.com/namespaceida__hexrays.html#a5dbc567822242aa3a25402cd87a9b8d5>
    '''
    # TODO: Make this an internal function and put the arg_functions into decompile() ?
    if not _ida_hexrays.init_hexrays_plugin():
        log_print(f"The decompiler for this architecture ({input_file.processor}) is not loaded.", arg_debug, arg_type="ERROR")
        return False

    if arg_functions:
        arg_functions = [address(func, arg_debug=arg_debug) for func in arg_functions]
        log_print(f"Decompiling {len(arg_functions)} functions", arg_type="INFO")
    else:
        log_print("Decompiling all functions", arg_type="INFO")

    log_print(f"Decompiling to {arg_outfile}", arg_type="INFO")
    res = _ida_hexrays.decompile_many(arg_outfile, arg_functions, arg_flags)
    log_print(f"done: Decompiling to {arg_outfile}", arg_type="INFO")
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def pseudocode(arg_ea: EvaluateType,
               arg_force_fresh_decompilation: bool = True,
               arg_debug: bool = False) -> str:
    ''' Get the pseudo code for a function. To work with the object (cfunc_t) use decompile() '''

    l_cfunc = decompile(arg_ea, arg_force_fresh_decompilation=arg_force_fresh_decompilation, arg_debug=arg_debug)
    if l_cfunc is None:
        log_print(f"decompile({_hex_str_if_int(arg_ea)}) failed", arg_type="ERROR")
        return f"<<< Could NOT decompile function at {_hex_str_if_int(arg_ea)} >>>"
    return str(l_cfunc.get_pseudocode())

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def decompiler_comments(arg_regexp: str = "",
                        arg_allow_library_functions: bool = True,
                        arg_debug: bool = False) -> Dict[int, str]:
    ''' Returns all user set comments from decompiler view
    @param arg_regexp Filter to only include comments that match this regexp.
    If arg_regexp == "" then include all comments

    @return Dict[ea: int, comment: str]
    '''
    res = {}
    for func_start in functions(arg_allow_library_functions=arg_allow_library_functions, arg_debug=arg_debug):
        l_comments = _ida_hexrays.restore_user_cmts(func_start)
        if l_comments is None:
            continue

        for l_tree_location, l_comment in l_comments.iteritems():
            if not arg_regexp or re.fullmatch(arg_regexp, str(l_comment)):
                res[l_tree_location.ea] = str(l_comment) # Maybe interesting in the future: _int_to_str_dict_from_module("_ida_hexrays", "ITP_.*")[l_tree_location.itp]
        _ida_hexrays.user_cmts_free(l_comments)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def decompiler_variable(arg_function: EvaluateType,
                        arg_variable_name: Union[str, _ida_hexrays.lvar_t],
                        arg_debug: bool = False
                        ) -> Optional[_ida_hexrays.lvar_t]:
    ''' Find the local variable (_ida_hexrays.lvar_t) given the function and the name seen in the pseudocode view '''
    if isinstance(arg_variable_name, _ida_hexrays.lvar_t):
        return arg_variable_name

    l_cfunc = decompile(arg_function, arg_force_fresh_decompilation=True, arg_debug=arg_debug)
    if l_cfunc is None:
        log_print("l_cfunc is None", arg_type="ERROR")
        return None

    for l_variable in l_cfunc.lvars:
        if l_variable.name == arg_variable_name:
            return l_variable
    log_print(f"Could not find any variable with the name '{arg_variable_name}'", arg_type="ERROR")
    return None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def decompiler_variable_set_name(arg_function: EvaluateType,
                                 arg_variable: Union[str, _ida_hexrays.lvar_t],
                                 arg_new_variable_name: str,
                                 arg_debug: bool = False) -> Optional[bool]:
    ''' Rename a pseudocode local variable (ida_hexrays.lvar_t) in the decompiler view given the function and the name as it seen in the pseudo code view '''

    l_function_temp = function(arg_function, arg_debug=arg_debug)
    if l_function_temp is None:
        log_print(f"Not a function at the given arg_function: {_hex_str_if_int(arg_function)}", arg_type="ERROR")
        return None

    l_function_address = l_function_temp.start_ea
    l_lvar_saved_info = _ida_hexrays.lvar_saved_info_t()
    l_lvar = decompiler_variable(l_function_address, arg_variable, arg_debug=arg_debug)
    if l_lvar is None:
        log_print("l_lvar is None", arg_type="ERROR")
        return None
    l_lvar_saved_info.ll = l_lvar # ll --> Local variable Locator # TODO: If l_lvar is None, then the call to modify_user_lvar_info() crash IDA
    l_lvar_saved_info.name = arg_new_variable_name
    return _ida_hexrays.modify_user_lvar_info(l_function_address, _ida_hexrays.MLI_NAME, l_lvar_saved_info)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def decompiler_variable_set_type(arg_function: EvaluateType,
                                 arg_variable: Union[str, _ida_hexrays.lvar_t],
                                 arg_new_type: Union[str, _ida_typeinf.tinfo_t],
                                 arg_debug: bool = False) -> Optional[bool]:
    ''' Change type of a pseudocode local variable (lvar) in the decompiler view given the function and the name as it seen in the pseudo code view '''

    l_function_address = address(function(arg_function, arg_debug=arg_debug), arg_debug=arg_debug)
    if l_function_address == _ida_idaapi.BADADDR:
        log_print(f"Not a function at the given arg_function: {_hex_str_if_int(arg_function)}", arg_type="ERROR")
        return None

    l_lvar_saved_info = _ida_hexrays.lvar_saved_info_t()
    l_lvar = decompiler_variable(l_function_address, arg_variable, arg_debug=arg_debug)
    if l_lvar is None:
        log_print("l_lvar is None", arg_type="ERROR")
        return None
    l_lvar_saved_info.ll = l_lvar
    l_type = get_type(arg_new_type, arg_debug=arg_debug)
    if l_type is None:
        log_print("l_type is not usable", arg_type="ERROR")
        return None
    l_lvar_saved_info.type = l_type
    return _ida_hexrays.modify_user_lvar_info(l_function_address, _ida_hexrays.MLI_TYPE, l_lvar_saved_info)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _read_range_selection(arg_v: Any = None) -> Tuple[bool, int, int]:
    ''' Reads the selected addresses that you selected with your mouse (or keyboard)

    @param arg_v According to Hexrays, it's a TWidget* which I cannot find any python type for atm. None means "the last used widget"
    @return (valid_selection: bool, sel_start: int, sel_end: int)

    Replacement for ida_kernwin.read_range_selection()
    '''
    valid_selection, start_address, end_address = _ida_kernwin.read_range_selection(arg_v)
    if not valid_selection:
        return (False, 0, 0)

    return (valid_selection, start_address, end_address)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def dump_to_disk(arg_ea_start: EvaluateType = 0,
                 arg_len: EvaluateType = 0,
                 arg_filename: Optional[str] = None,
                 arg_xor_key: Optional[BufferType] = None,
                 arg_debug: bool = False
                 ) -> Optional[str]:
    ''' Dump bytes from the IDB to a file on disk.
    The hotkey is in the global variable "DUMP_TO_DISK_HOTKEY" and is default set to 'w'

    @param arg_filename is this is set to the magic value "|clipboard|" then we will copy the string to the clipboard instead of writing it to disk

    @return is the filename we wrote the bytes to
    '''

    if arg_ea_start and not arg_len:
        log_print("You need to give arg_ea_start and arg_len OR select the range of bytes you want to dump.", arg_type="ERROR")
        return None

    valid_selection, sel_start, sel_end = _read_range_selection()
    if valid_selection:
        arg_ea_start = min(sel_start, sel_end)
        l_len: int = max(sel_end, sel_start) - arg_ea_start
        log_print(f"sel_start: 0x{sel_start:x}, sel_end: 0x{sel_end:x}, l_len: 0x{l_len:x}", arg_debug)
    else:
        arg_ea_start = address(arg_ea_start, arg_debug=arg_debug)
        l_temp_len = eval_expression(arg_len, arg_debug=arg_debug)
        if l_temp_len is None:
            log_print("eval_expression(arg_len) failed", arg_type="ERROR")
            return None
        l_len = l_temp_len

    if arg_ea_start == _ida_idaapi.BADADDR or not l_len:
        log_print("You need to give arg_ea_start and arg_len OR select the range of bytes you want to dump.", arg_type="ERROR")
        return None

    l_temp_bytes: Optional[bytes] = read_bytes(arg_ea_start, l_len, arg_debug=arg_debug)
    if l_temp_bytes is None:
        log_print(f'read_bytes({_hex_str_if_int(arg_ea_start)}) failed', arg_type="ERROR")
        return None

    bytes_from_IDB: bytearray = bytearray(l_temp_bytes)
    if arg_xor_key is not None:
        arg_xor_key = hex_parse(arg_xor_key, arg_debug=arg_debug)
        if not arg_xor_key:
            log_print("Invalid arg_xor_key, could not find any way to parse it as a hex string.", arg_type="ERROR")
            return None
        for i in range(0, len(bytes_from_IDB)):
            bytes_from_IDB[i] ^= bytearray.fromhex(arg_xor_key[i % len(arg_xor_key)])[0]
    else:
        arg_xor_key = []
    if not arg_filename:
        arg_filename = f"{input_file.idb_path}.0x{arg_ea_start:x}_0x{l_len:x}"

        if arg_xor_key:
            arg_filename += f".xor_key_{''.join(arg_xor_key)}"

        arg_filename += ".dump"

    if arg_filename == "|clipboard|":
        l_temp = hex_parse(bytes_from_IDB, arg_debug=arg_debug)
        l_hex_text = " ".join(l_temp)
        log_print(f"Going to copy the following string into the clipboard: {l_hex_text}", arg_debug)
        clipboard_copy(l_hex_text, arg_debug=arg_debug)
    else:
        with open(arg_filename, "wb") as f:
            f.write(bytes_from_IDB)

    log_print(f"{'selected bytes' if valid_selection else 'function call'} dumped 0x{l_len:x} bytes from 0x{arg_ea_start:x} to '{arg_filename}' XORed with '{' '.join(arg_xor_key)}' ", arg_type="INFO")
    return arg_filename

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def bookmark(arg_ea: EvaluateType, arg_description: Optional[str] = None, arg_debug: bool = False) -> Optional[str]:
    ''' Get bookmark at given EA (Effective Address), returns an empty str "" if there is no bookmark on that EA
    IDA has started to call these "marked positions"
    Read more on g get_marked_pos: <https://python.docs.hex-rays.com/namespaceida__idc.html#ad6bd46f0c4480099a566425b7a36fcda>
    Read more on mark_position: <https://python.docs.hex-rays.com/namespaceida__idc.html#a38ff959f787390b08b1b41f931809c84>
    Read more on IDC reference: <https://docs.hex-rays.com/developer-guide/idc/idc-api-reference/alphabetical-list-of-idc-functions/367>
    You can delete a bookmark by setting arg_description = ""
    @param arg_ea The address you want the bookmark on
    @param arg_description if this is set, then we create a bookmark on that ea (overwriting whatever was there before), if this is the empty str, the the bookmark is deleted
    @return description: str
    '''

    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    if arg_description is not None:
        # Taken from <https://docs.hex-rays.com/developer-guide/idc/idc-api-reference/alphabetical-list-of-idc-functions/367>
        # ea      - address to mark
        # lnnum   - number of generated line for the 'ea'
        # x       - x coordinate of cursor
        # y       - y coordinate of cursor
        # slot    - slot number: 0..1023
        #           if the specified value is not within the range, IDA will ask the user to select slot.
        # comment - description of the mark.
        #           Should be not empty.
        # returns: none

        # Need to find first empty slot for our bookmark
        for bookmark_slot in range(0, 1024):
            l_ea = _ida_idc.get_marked_pos(bookmark_slot)
            if l_ea in (_ida_idaapi.BADADDR, l_addr):
                break

        if l_ea == _ida_idaapi.BADADDR and arg_description == "":
            log_print("We got a delete bookmark on an ea that does not have a bookmark, ignoring", arg_type="WARNING")
            return ""

        _ida_idc.mark_position(ea=l_addr, lnnum=0, x=0, y=0, slot=bookmark_slot, comment=arg_description) # https://python.docs.hex-rays.com/namespaceida__idc.html#a38ff959f787390b08b1b41f931809c84

    if arg_description == "": # This means to delete a bookmark
        return ""

    for bookmark_slot in range(0, 1024):
        l_ea = _ida_idc.get_marked_pos(bookmark_slot)
        if l_ea == l_addr:
            return _ida_idc.get_mark_comment(bookmark_slot)
        if l_ea == _ida_idaapi.BADADDR:
            log_print(f"ida_idc.get_marked_pos({bookmark_slot}) returned BADADDR", arg_type="ERROR")
            return ""

    return None # We should never get there

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def bookmarks(arg_debug: bool = False) -> Optional[List[Tuple[int, str]]]:
    ''' Get all bookmarks as a list of tuples. The tuple looks like: (ea: int, description: str)
    Read more: <https://hex-rays.com/blog/igors-tip-of-the-week-80-bookmarks>
    @return List[(ea: int, description: str)]
    '''
    res = []
    for bookmark_slot in range(0, 1024):
        l_ea = _ida_idc.get_marked_pos(bookmark_slot)
        if l_ea == _ida_idaapi.BADADDR:
            log_print(f"ida_idc.get_marked_pos({bookmark_slot}) returned BADADDR", arg_actually_print=arg_debug, arg_type="ERROR")
            break
        res.append((l_ea, _ida_idc.get_mark_comment(bookmark_slot)))

    return res

# ---- Hotkey: w --> Dump selected bytes to a file on disk ----------------------------------------------------------------------------------------
_ACTION_NAME_DUMP_SELECTED_BYTES = f"{__name__}:dump_selected_bytes_to_disk"

if _ACTION_NAME_DUMP_SELECTED_BYTES in _ida_kernwin.get_registered_actions():
    if _ida_kernwin.unregister_action(_ACTION_NAME_DUMP_SELECTED_BYTES):
        log_print(f"unregister_action(): '{_ACTION_NAME_DUMP_SELECTED_BYTES}' OK", arg_type="INFO")
    else:
        log_print(f"unregister_action(): '{_ACTION_NAME_DUMP_SELECTED_BYTES}' failed", arg_type="ERROR")

class ActionHandlerDumpToDisk(_ida_kernwin.action_handler_t):
    ''' Handler for dump to disk '''
    @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
    def activate(self, ctx: _ida_kernwin.action_ctx_base_t):
        ''' This code is run when the hotkey is pressed '''
        del ctx # Not used but needed in prototype
        l_debug: bool = False
        log_print("ActionHandlerDumpToDisk activate", l_debug)
        _ = dump_to_disk(arg_debug=l_debug) # Without arguments --> selected bytes
        return 1

    @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
    def update(self, ctx: _ida_kernwin.action_ctx_base_t):
        ''' This function is called whenever something has changed, and you can tell IDA in here when you want your update() function to be called. '''
        del ctx # Not used but needed in prototype
        return _ida_kernwin.AST_ENABLE_ALWAYS # This hotkey should be available everywhere

if _ida_kernwin.register_action(_ida_kernwin.action_desc_t(_ACTION_NAME_DUMP_SELECTED_BYTES, f"{__name__}: Dump selected bytes to disk", ActionHandlerDumpToDisk(), HOTKEY_DUMP_TO_DISK)):
    log_print(f"register_action('{_ACTION_NAME_DUMP_SELECTED_BYTES}') OK", arg_type="INFO")
else:
    log_print(f"register_action('{_ACTION_NAME_DUMP_SELECTED_BYTES}') failed", arg_type="ERROR")

# ---- Hotkey: Shift + C --> Copy selected bytes as hex text to clipboard ----------------------------------------------------------------------------------------
_ACTION_NAME_COPY_HEX_TEXT = f"{__name__}:copy_hex_text"
if _ACTION_NAME_COPY_HEX_TEXT in _ida_kernwin.get_registered_actions():
    if _ida_kernwin.unregister_action(_ACTION_NAME_COPY_HEX_TEXT):
        log_print(f"unregister_action(): '{_ACTION_NAME_COPY_HEX_TEXT}' OK", arg_type="INFO")
    else:
        log_print(f"unregister_action(): '{_ACTION_NAME_COPY_HEX_TEXT}' failed", arg_type="ERROR")

class ActionHandlerCopyHexText(_ida_kernwin.action_handler_t):
    ''' Handler for copy hex text '''
    @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
    def activate(self, ctx: _ida_kernwin.action_ctx_base_t):
        ''' This code is run when the hotkey is pressed '''
        del ctx # Not used but needed in prototype
        l_debug: bool = False
        log_print("ActionHandlerCopyHexText activate", l_debug)
        copy_hex_text_to_clipboard() # Without arguments --> Copy selected bytes as hex text
        return 1

    @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
    def update(self, ctx: _ida_kernwin.action_ctx_base_t):
        ''' This function is called whenever something has changed, and you can tell IDA in here when you want your update() function to be called. '''
        del ctx # Not used but needed in prototype
        return _ida_kernwin.AST_ENABLE_ALWAYS # This hotkey should be available everywhere

if _ida_kernwin.register_action(_ida_kernwin.action_desc_t(_ACTION_NAME_COPY_HEX_TEXT, f"{__name__}: Copy selected bytes as hex text", ActionHandlerCopyHexText(), HOTKEY_COPY_SELECTED_BYTES_AS_HEX_TEXT)):
    log_print(f"register_action('{_ACTION_NAME_COPY_HEX_TEXT}') OK", arg_type="INFO")
else:
    log_print(f"register_action('{_ACTION_NAME_COPY_HEX_TEXT}') failed", arg_type="ERROR")

# ---- Hotkey: Alt + Ins --> Copy current address ----------------------------------------------------------------------------------------
_ACTION_NAME_COPY_CURRENT_ADDRESS = f"{__name__}:copy_current_address"
if _ACTION_NAME_COPY_CURRENT_ADDRESS in _ida_kernwin.get_registered_actions():
    if _ida_kernwin.unregister_action(_ACTION_NAME_COPY_CURRENT_ADDRESS):
        log_print(f"unregister_action(): '{_ACTION_NAME_COPY_CURRENT_ADDRESS}' OK", arg_type="INFO")
    else:
        log_print(f"unregister_action(): '{_ACTION_NAME_COPY_CURRENT_ADDRESS}' failed", arg_type="ERROR")

class ActionHandlerCopyCurrentAddress(_ida_kernwin.action_handler_t):
    ''' Handler for copy current address '''
    @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
    def activate(self, ctx: _ida_kernwin.action_ctx_base_t):
        ''' This code is run when the hotkey is pressed '''
        del ctx # Not used but needed in prototype
        l_debug: bool = False
        log_print("ActionHandlerCopyCurrentAddress activate", l_debug)
        _ = clipboard_copy(f'0x{current_address():x}')
        return 1

    @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
    def update(self, ctx: _ida_kernwin.action_ctx_base_t):
        ''' This function is called whenever something has changed, and you can tell IDA in here when you want your update() function to be called. '''
        del ctx # Not used but needed in prototype
        return _ida_kernwin.AST_ENABLE_ALWAYS # This hotkey should be available everywhere

if _ida_kernwin.register_action(_ida_kernwin.action_desc_t(_ACTION_NAME_COPY_CURRENT_ADDRESS, f"{__name__}: Copy the current address as hex text", ActionHandlerCopyCurrentAddress(), HOTKEY_COPY_CURRENT_ADDRESS)):
    log_print(f"register_action('{_ACTION_NAME_COPY_CURRENT_ADDRESS}') OK", arg_type="INFO")
else:
    log_print(f"register_action('{_ACTION_NAME_COPY_CURRENT_ADDRESS}') failed", arg_type="ERROR")

# -------------------------------------------------------------------------------------------------------------------------------------------------------
@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _ea_to_hexrays_insn(arg_ea: EvaluateType,
                        arg_cached_cfunc: Optional[_ida_hexrays.cfuncptr_t] = None,
                        arg_force_fresh_decompilation: bool = False,
                        arg_debug: bool = False
                        ) -> Optional[_ida_hexrays.cinsn_t]:
    ''' Internal function. The decompiled AST is made up of ida_hexrays.cinsn_t, this function finds the correct ida_hexrays.cinsn_t given an EA (Effective Address) '''
    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    if not arg_cached_cfunc:
        arg_cached_cfunc = decompile(l_addr, arg_force_fresh_decompilation=arg_force_fresh_decompilation, arg_debug=arg_debug)
    if not arg_cached_cfunc:
        return None

    # OBS! I know there is a shorter and faster way with arg_cached_cfunc.eamap.get(ea, None) but I used the long code to have debug output during development
    ea: int
    vector_of_insn: List[_ida_hexrays.cinsn_t]
    for ea, vector_of_insn in arg_cached_cfunc.eamap.items(): # eamap maps ea_t --> vector<ida_hexrays.cinsn_t>.
        vector_idx = 0
        res: _ida_hexrays.cinsn_t = _ida_hexrays.cinsn_t()

        for insn in vector_of_insn: # This can be multiple insn but they can be wrong. How to find the correct one? This is most probably a bug in IDA cause I get vectors that look like <return -1, call function, return -1> where the call is the expected and the "return -1"s are wrong
            if arg_debug:
                if insn.is_epilog():
                    log_print(f"ea: {ea:x} is INS_EPILOG", arg_debug)
                    continue
                log_print(f"ea: {ea:x} --> insn.ea: {insn.ea:x} --> vector_idx: {vector_idx} --> {_ida_lines.tag_remove(insn.print1(None))}", arg_debug)
                vector_idx += 1
            if ea == l_addr:
                log_print(f"Match l_addr: 0x{l_addr:x} --> take the longest (most info) and return that. len(vector_of_insn): {len(vector_of_insn)}", arg_debug)
                if insn.is_epilog():
                    log_print(f"l_addr 0x{l_addr:x} is epilog", arg_debug)
                    continue
                res = insn if len(str(insn)) > len(str(res)) else res
                log_print(f"res: {res}", arg_debug)
                log_print(f"res.ea: {_hex_str_if_int(res.ea)}", arg_debug)

            if ea > l_addr:
                log_print(f"ea: 0x{ea:x} > l_addr: 0x{l_addr:x} means we are past our address we are looking for", arg_debug)
                return None
        if res.ea != _ida_idaapi.BADADDR:
            return res

    return None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def decompiled_line(arg_ea: EvaluateType, arg_cached_cfunc: Optional[_ida_hexrays.cfuncptr_t] = None, arg_debug: bool = False) -> str:
    ''' Sometimes you want only 1 line from the decompilation. See example in my plugins show_global_xrefs_hx.py and xor_finder.py '''

    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return f"<<< Failed to find '{_hex_str_if_int(arg_ea)}' >>>"

    if arg_cached_cfunc is None:
        arg_cached_cfunc = decompile(l_addr, arg_debug=arg_debug)
    if not arg_cached_cfunc:
        log_print(f"{_hex_str_if_int(l_addr)} could not be decompiled", arg_debug, arg_type="ERROR")
        return "<<< Could not decompile >>>"

    # The "correct" way to do it is as follows:
    # return _ida_lines.tag_remove(arg_cached_cfunc.body.find_parent_of(arg_cached_cfunc.body.find_closest_addr(l_addr)).print1(arg_cached_cfunc))
    # BUT it's wrong. If you put in the address of a part of the epilog, then find_closest_addr() will return the line closest above it.
    # You can also put in any other address that is not a valid part of a function. This will return the last line in the function above that is correct. Test by taking the "align 10h" between functions as input address

    l_insn: Optional[_ida_hexrays.cinsn_t] = _ea_to_hexrays_insn(l_addr, arg_cached_cfunc, arg_debug=arg_debug)
    if l_insn is None:
        return f"<<< _ea_to_hexrays_insn(0x{l_addr:x}) returned None >>>"
    if l_insn.is_epilog(): # This means that the address that is given doesn't have any pseudo code since it's something the compiler added for maintaince
        return f"<<< _ea_to_hexrays_insn(0x{l_addr:x}).is_epilog() == True >>>"

    res = _ida_lines.tag_remove(l_insn.print1(arg_cached_cfunc))
    res = res.replace(';', '; ')
    res = _whitespace_zapper(res).strip()
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def function_prototype(arg_function_name_or_ea: EvaluateType,
                       arg_cached_cfunc: Optional[_ida_hexrays.cfuncptr_t] = None,
                       arg_allow_comments: bool = True,
                       arg_force_fresh_decompilation: bool = False,
                       arg_debug: bool = False
                       ) -> str:
    ''' Returns the function prototype including the function name and the comments as 1 line.
    You can use str(get_type(ea)) but that command will NOT give the comments.
    '''

    if arg_force_fresh_decompilation or arg_cached_cfunc is None:
        # log_print(f"Calling decompile({arg_function_name_or_ea})")
        arg_cached_cfunc = decompile(arg_function_name_or_ea, arg_force_fresh_decompilation=arg_force_fresh_decompilation, arg_debug=arg_debug)
    if not arg_cached_cfunc:
        log_print(f"Since we failed to decompile {_hex_str_if_int(arg_function_name_or_ea)}, we are calling str(get_type({_hex_str_if_int(arg_function_name_or_ea)}, arg_debug={arg_debug}))", arg_type="INFO")
        return str(get_type(arg_function_name_or_ea, arg_debug=arg_debug))

    l_function_prototype: str = _ida_lines.tag_remove(arg_cached_cfunc.print_dcl()) + ';'
    if arg_allow_comments:
        l_comment: str = _comment_get(arg_function_name_or_ea, arg_debug=arg_debug)
        if l_comment:
            l_function_prototype += " // " + l_comment

    return l_function_prototype

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_get_func_name(arg_ea: int) -> str:
    ''' Wrapper for ida_funcs.get_func_name()
    IDA Bug: The docstring say "@return: length of the function name" which is wrong

    Tag: community fix, IDA bug
    '''
    l_get_func_name_res = _ida_funcs.get_func_name(arg_ea)
    return l_get_func_name_res or  ""

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def name(arg_ea: EvaluateType,
         arg_set_name: Optional[str] = None,
         arg_flags: int = _ida_name.SN_NOWARN | _ida_name.SN_NOCHECK,
         arg_force: bool = False,
         arg_demangle_name: bool = False,
         arg_debug: bool = False
         ) -> Optional[str]:
    ''' Gets or sets the name at the given EA (Effective Address)

    To remove a name (and give the function a name that IDA picks, use arg_set_name = ""
    @param arg_force: If the name exists, then append functionname_X incremental. Same as "Rename global item" in the decompiler.

    @return The name as str

    Replacement for ida_name.get_name_ea() and ida_name.set_name()

    '''
    if isinstance(arg_ea, _ida_hexrays.lvar_t):
        res = arg_ea.name
        log_print(f"arg_ea is ida_hexrays.lvar_t, so instead of looking up the address, I use the member 'name' == {res}", arg_debug)
        return res

    if isinstance(arg_ea, _ida_idd.modinfo_t):
        res = arg_ea.name
        log_print(f"arg_ea is ida_idd.modinfo_t, so instead of looking up the address, I use the member 'name' == {res}", arg_debug)
        return res

    if isinstance(arg_ea, _ida_ua.op_t) and arg_ea.type == _ida_ua.o_reg:
        res = arg_ea.register.name
        log_print(f"arg_ea is ida_ua.op_t, so instead of looking up the address, use the register name == {res}", arg_debug)
        return res

    if isinstance(arg_ea, _ida_segment.segment_t):
        res = _ida_segment.get_segm_name(arg_ea)
        log_print(f"arg_ea is ida_segment.segment_t, so instead of looking up the address, use the segment name: {res}", arg_debug)
        return res

    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    if arg_set_name is not None:
        res = _ida_name.set_name(l_addr, arg_set_name, arg_flags)
        if not res and arg_force:
            res = _ida_name.force_name(l_addr, arg_set_name) # If the name exists, then append functionname_X incremental
            log_print(f"ida_name.force_name() returned {res}", arg_debug)

    l_address_formatstring = "016X" if input_file.bits == 64 else "08X"

    l_function_name: str = _idaapi_get_func_name(l_addr)
    if l_function_name:
        log_print(f"_get_func_name(0x{l_addr:x}) returned {l_function_name}", arg_debug)
        l_func_start: int = address(l_function_name, arg_debug=arg_debug)
        l_diff = l_addr - l_func_start
        l_name: str = demangle_string(l_function_name, arg_debug=arg_debug) if arg_demangle_name else l_function_name
        l_name = _ida_name.get_long_name(l_func_start) if l_name is None else l_name
        if not l_diff:
            return l_name
        return f"{l_name} + 0x{l_diff:x}"

    l_name = _ida_name.get_long_name(l_addr) if arg_demangle_name else _ida_name.get_name(l_addr)
    if l_name:
        return l_name

    l_item_head = _ida_bytes.get_item_head(l_addr)
    if l_item_head != l_addr:
        res = f"{name(l_item_head, arg_debug=arg_debug)} + 0x{l_addr - l_item_head:x}"
        return res

    return f"{l_addr:{l_address_formatstring}}"

label = name # Other programs use the term label

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_demangle_name(arg_name: str, arg_disable_mask: int, arg_demreq=_ida_name.DQT_FULL) -> str:
    ''' Wrapper around ida_name.demangle_name()
    IDA bug: Docstring say "demangle_name(name, disable_mask, demreq=DQT_FULL) -> int32" which is wrong
    In idc.py, we can read "If the input name cannot be demangled, returns None"

    @return Returns the demangled name, empty str "" on fail
    '''
    return _ida_name.demangle_name(arg_name, arg_disable_mask, arg_demreq) or ""

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def demangle_string(arg_mangled_name: str,
                  arg_flags: int = 0,
                  arg_debug: bool = False,
                  arg_allow_brute_force: bool = False
                  ) -> str:
    ''' Demangles a string. Can try to brute force demangle some names that IDA usually doesn't like.
    @param arg_flags: int extra flags to ida_name.demangle_name(). To he honest, I don't know what these flags are.

    @return Returns the demangled name, empty str "" on fail
    '''
    res = _idaapi_demangle_name(arg_mangled_name, arg_flags)
    if not res:
        if arg_allow_brute_force:
            for i in range(1, len(arg_mangled_name)):
                res = _idaapi_demangle_name(arg_mangled_name[i:], arg_flags)
                log_print(f"ida_name.demangle_name('{arg_mangled_name[i:]}', {arg_flags}) resulted in {res} on try number {i}", arg_debug)
                if res != "":
                    return res
        log_print(f"Could not demangle the name '{arg_mangled_name}' in any meaningful way", arg_type="WARNING")
        return ""

    log_print(f"ida_name.demangle_name('{arg_mangled_name}', {arg_flags}) resulted in {res}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def comment(arg_ea: EvaluateType,
            arg_set_comment: Optional[str] = None,
            arg_add_source: bool = True,
            arg_oneliner: bool = False,
            arg_cached_cfunc: Optional[_ida_hexrays.cfuncptr_t] = None,
            arg_type_of_comment: Optional[int] = None,
            arg_debug: bool = False
            ) -> Optional[str]:
    '''
    This is a unified entry to comments. There are 2 functions named _comment_get() and _comment_set() that can be used but this function should be the only one you need.

    Comments can be at many different levels at the same address.
    This function returns the user comments as one string reading in the order:
    1. decompiler
    2. disassembly
    3. disassembly repeatable
    4. function comment
    5. function repeatable comment

    arg_type_of_comment is one of ida_hexrays.ITP_* where _ida_hexrays.ITP_BLOCK1 is the line above. Default is None --> test all and take the first one working
    '''

    if arg_set_comment is not None:
        l_set_comment_res = _comment_set(arg_ea=arg_ea, arg_comment=arg_set_comment, arg_cached_cfunc=arg_cached_cfunc, arg_type_of_comment=arg_type_of_comment, arg_debug=arg_debug)
        if not l_set_comment_res:
            log_print(f"_comment_set({_hex_str_if_int(arg_ea)}, {arg_set_comment}) returned False", arg_type="ERROR")
            return None

    return _comment_get(arg_ea=arg_ea, arg_cached_cfunc=arg_cached_cfunc, arg_add_source=arg_add_source, arg_oneliner=arg_oneliner, arg_debug=arg_debug)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _comment_get(arg_ea: EvaluateType,
                arg_cached_cfunc: Optional[_ida_hexrays.cfuncptr_t] = None,
                arg_add_source: bool = True,
                arg_oneliner: bool = False,
                arg_debug: bool = False) -> str:
    ''' Internal function. Use comment() '''

    l_addr = address(arg_ea, arg_debug=arg_debug)
    res = ""
    if not arg_cached_cfunc and is_code(l_addr):
        arg_cached_cfunc = decompile(l_addr, arg_debug=arg_debug)
    if arg_cached_cfunc:
        insn: Optional[_ida_hexrays.cinsn_t] = _ea_to_hexrays_insn(l_addr, arg_cached_cfunc, arg_debug=arg_debug)
        if insn and not insn.is_epilog():
            ea = insn.ea
            cmts = _ida_hexrays.restore_user_cmts(arg_cached_cfunc.entry_ea)

            if cmts is not None:
                for tree_location, cmt in cmts.items(): # tree_location == treeloc_t
                    log_print(f"tree_location.ea: {tree_location.ea:x} --> {str(cmt)}", arg_debug)
                    if tree_location.ea == ea:
                        res += str(cmt).strip() # There can be many comment on the same address, like after the ; and on the line before
            _ida_hexrays.user_cmts_free(cmts)
            res = res.strip()
            if arg_add_source and res:
                res += "  [decompiler]; "

    # No decompiler comments, let's try the old ones
    is_repeatable = False
    _disassembly_comment = _ida_bytes.get_cmt(l_addr, is_repeatable) # Get the comment on that line
    if _disassembly_comment:
        res += _disassembly_comment
        if arg_add_source:
            res += "  [disassembly]; "

    is_repeatable = True
    _disassembly_comment_repeatable = _ida_bytes.get_cmt(l_addr, is_repeatable)
    if _disassembly_comment_repeatable:
        res += _disassembly_comment_repeatable
        if arg_add_source:
            res += "  [disassembly repeatable]; "

    is_repeatable = False
    _function_comment = _ida_funcs.get_func_cmt(_ida_funcs.get_func(l_addr), is_repeatable)
    if _function_comment:
        res += _function_comment
        if arg_add_source:
            res += "  [function]; "

    is_repeatable = True
    _function_comment_repeatable = _ida_funcs.get_func_cmt(_ida_funcs.get_func(l_addr), is_repeatable)
    if _function_comment_repeatable:
        res += _function_comment_repeatable
        if arg_add_source:
            res += "  [function repeatable]; "

    if arg_oneliner:
        res = res.replace('\n', '; ')

    return res.strip()

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _comment_set(arg_ea: EvaluateType,
                arg_comment: str,
                arg_cached_cfunc: Optional[_ida_hexrays.cfuncptr_t] = None,
                arg_type_of_comment: Optional[int] = None,
                arg_debug: bool = False
                ) -> bool:
    ''' Internal function. Use comment(). Comments can be set at many different levels at the same address.
    This function sets the decompiler comment (if possible) and the disassembly view.
    arg_type_of_comment is one of ida_hexrays.ITP_* where ida_hexrays.ITP_BLOCK1 is the line above
    '''

    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    res = True
    # Set the comment in the decompiler view (if possible)
    if not arg_cached_cfunc and is_code(l_addr):
        arg_cached_cfunc = decompile(l_addr, arg_debug=arg_debug)
    if arg_cached_cfunc:
        insn = _ea_to_hexrays_insn(l_addr, arg_debug=arg_debug)
        if not insn:
            log_print(f"_ea_to_hexrays_insn(0x{l_addr:x}) returned None", arg_type="ERROR")
            return False

        if insn.is_epilog():
            log_print("insn.is_epilog() == True", arg_type="ERROR")
            return False

        tree_location = _ida_hexrays.treeloc_t()
        tree_location.ea = insn.ea

        dict_of_types_of_comments: Dict[int, str] = {
            _ida_hexrays.ITP_SEMI :   "SEMI",   # ';'
            _ida_hexrays.ITP_CURLY1 : "CURLY1", # '{'
            _ida_hexrays.ITP_CURLY2 : "CURLY2", # '}'
            _ida_hexrays.ITP_BRACE1 : "BRACE1", # '(' Same as ida_hexrays.ITP_INNER_LAST
            _ida_hexrays.ITP_BRACE2 : "BRACE2", # ')'
            _ida_hexrays.ITP_COLON :  "COLON",  # ':'
            _ida_hexrays.ITP_ARG1 :   "ARG1",
            _ida_hexrays.ITP_ARG64 :  "ARG64",
            _ida_hexrays.ITP_CASE :   "CASE",
            _ida_hexrays.ITP_DO :     "DO",
            _ida_hexrays.ITP_ELSE :   "ELSE",
            _ida_hexrays.ITP_ASM :    "ASM",
            _ida_hexrays.ITP_EMPTY :  "EMPTY",
            _ida_hexrays.ITP_SIGN :   "SIGN",
            _ida_hexrays.ITP_BLOCK1 : "BLOCK1", # This means line above ( ITP_BLOCK1 == 74 )
            _ida_hexrays.ITP_BLOCK2 : "BLOCK2"  # No idea what this is  ( ITP_BLOCK2 == 75 )
            # _ida_hexrays.ITP_INNER_LAST : "INNER_LAST", # _ida_hexrays.ITP_INNER_LAST == _ida_hexrays.ITP_BRACE1 == 65, bug?
        }

        if arg_type_of_comment:
            if arg_type_of_comment not in dict_of_types_of_comments:
                log_print(f"arg_type_of_comment: {arg_type_of_comment} is not valid. It should be one of _ida_hexrays.ITP_*", arg_type="ERROR")
                return False

            _replacement_dict_of_types_of_comments = {}
            _replacement_dict_of_types_of_comments[arg_type_of_comment] = dict_of_types_of_comments[arg_type_of_comment]
            dict_of_types_of_comments = _replacement_dict_of_types_of_comments

        # The following for loop is REALLY ugly but I can't find any better way to do this :-(
        l_decompiler_comment_set_ok = False
        for itp in dict_of_types_of_comments:
            log_print(f"testing: arg_cached_cfunc.set_user_cmt(_addr = 0x{tree_location.ea:x}, itp = {dict_of_types_of_comments[itp]}, comment = '{arg_comment}')", arg_debug)
            tree_location.itp = itp
            arg_cached_cfunc.set_user_cmt(tree_location, arg_comment)
            arg_cached_cfunc.save_user_cmts()
            arg_cached_cfunc = decompile(l_addr, arg_force_fresh_decompilation=True) # Forced refresh
            if not arg_cached_cfunc.has_orphan_cmts():
                l_decompiler_comment_set_ok = True
                arg_cached_cfunc.save_user_cmts()
                log_print(f"arg_cached_cfunc.set_user_cmt(_addr = 0x{tree_location.ea:x}, itp = {dict_of_types_of_comments[itp]}, comment = '{arg_comment}') worked!", arg_debug)
                break
            arg_cached_cfunc.del_orphan_cmts()
            arg_cached_cfunc.save_user_cmts()

        if not l_decompiler_comment_set_ok:
            log_print("Could NOT set the decompiler comment correct. l_decompiler_comment_set_ok == False", arg_type="ERROR")

    # Set the comment in the disassembly view also
    l_is_repeatable = False
    log_print(f"_ida_bytes.set_cmt(0x{l_addr:x}, '{arg_comment}', is_repeatable = {l_is_repeatable})", arg_debug)
    res = _ida_bytes.set_cmt(l_addr, arg_comment, l_is_repeatable)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _comment_append(arg_ea: EvaluateType, arg_comment: str, arg_cached_cfunc: Optional[_ida_hexrays.cfuncptr_t] = None, arg_debug: bool = False) -> bool:
    ''' Comments can be set at many different levels at the same address.
    This function appends to the decompiler comment (if possible) and appends to the disassembly view
    If the comment you are appending already exists as comment at that address, then we do NOT append it again but still return True.
    '''

    l_old_cmt: str = _comment_get(arg_ea, arg_cached_cfunc=arg_cached_cfunc, arg_add_source=False, arg_debug=arg_debug)
    res = True
    if arg_comment not in l_old_cmt:
        l_marker = '; ' if l_old_cmt else ''
        res = _comment_set(arg_ea, f"{l_old_cmt}{l_marker}{arg_comment}", arg_cached_cfunc=arg_cached_cfunc, arg_debug=arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def is_library_function(arg_ea: EvaluateType, arg_heavy_analysis: bool = False, arg_debug: bool = False) -> Optional[bool]:
    ''' Is the given EA (Effective Address) in a function IDA thinks is incompiled library function? '''

    # TODO: This function should have an extra argument with "heavy analysis" that make heuristic checks (if the function is not already marked as libfunc) that checks:
    # 1. Neighboring functions, are they libfuncs?
    # 2. Are there any calls to NON libfuncs coming from this function?
    if isinstance(arg_ea, _ida_funcs.func_t):
        l_func: _ida_funcs.func_t = arg_ea
    else:
        l_addr = address(arg_ea, arg_debug=arg_debug)
        l_func = _ida_funcs.get_func(l_addr)
        if not l_func:
            log_print(f"arg_ea '{_hex_str_if_int(arg_ea)}' is not a valid function", arg_type="ERROR")
            return None

    if arg_heavy_analysis:
        log_print("Not yet implemented the arg_heavy_analysis", arg_type="ERROR")
    # Each function that has both its neighbors as library functions will also be marked as library functions
        # for i in range(1, len(all_functions) - 1):
            # if not is_library_function(all_functions[i]) and is_library_function(all_functions[i-1]) and is_library_function(all_functions[i+1]):
                # all_functions[i].flags = all_functions[i].flags | _ida_funcs.FUNC_LIB
                # _ida_funcs.update_func(all_functions[i])
                # log_print(f"function '{all_functions[i].name}' was changed to library function", arg_debug)



    return (l_func.flags & _ida_funcs.FUNC_LIB) != 0

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def functions(arg_allow_library_functions: bool = True, arg_debug: bool = False) -> List[int]:
    ''' List of functions in the program.
    Can be used to filter out library functions

    @return List[function_start_address: int]
    '''
    l_all_functions: List[int] = []
    for func_addr in _idautils.Functions():
        l_all_functions.append(func_addr)

    if arg_allow_library_functions:
        return l_all_functions

    res = [func for func in l_all_functions if not is_library_function(func, arg_debug=arg_debug)]
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def imports(arg_debug: bool = False) -> Dict[str, Dict[str, Tuple[int, int]]]:
    ''' Returns a dict with key: the module name and as value: another dict
    with key: function_name, value: tuple (function_ea, function_ordinal)
    ex: {'KERNEL32': {'CreateFileW': (0xaabbccdd, 0)}}
    '''

    l_tmp_imported_function_info_dict = {}
    res = {}

    def __import_callback(arg_ea, arg_name, arg_ordinal):
        if arg_name is None:
            arg_name = f"no_function_name_ordinal_{arg_ordinal}"

        l_tmp_imported_function_info_dict[arg_name] = (arg_ea, arg_ordinal)
        return True # return True -> Continue enumeration, return False -> Stop enumeration

    num_imported_modules = _ida_nalt.get_import_module_qty()
    for i in range(0, num_imported_modules):
        module_name = _ida_nalt.get_import_module_name(i).lower()
        log_print(f"Found imported module: {module_name} with index {i}", arg_debug)
        _ida_nalt.enum_import_names(i, __import_callback)
        res[module_name] = l_tmp_imported_function_info_dict
        # log_print(f"Module: {module_name} have the following imports: {[function_name for function_name in res[module_name]]}", arg_debug)
        l_tmp_imported_function_info_dict = {}

    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def exports(arg_debug: bool = False) -> Dict[int, Tuple[int, int, str]]:
    ''' Get all exported functions including start/entrypoint. The dict returned is Dict[ea: int] -> (index: int, ordinal: int, name: str) '''
    res = {}
    for index, ordinal, ea, l_name in _idautils.Entries():
        res[ea] = (index, ordinal, l_name)
    log_print(f"Len of exports: {len(res)}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def read_bytes(arg_ea: EvaluateType, arg_len: EvaluateType, arg_debug: bool = False) -> Optional[bytes]:
    ''' Read bytes from the IDB. OBS! The IDB might not match the file on disk or active memory.

    Replacement for ida_bytes.get_bytes()

    OBS! See ida_idd.dbg_read_memory(ea, size) for some other memory read
    '''
    debugger_refresh_memory_WARNING_VERY_EXPENSIVE() # If you have allocated memory via appcall, then IDA doesn't know about it until we refresh

    l_len: Optional[int] = eval_expression(arg_len, arg_debug=arg_debug)
    if l_len is None:
        log_print(f"arg_len is invalid. arg_len: '{arg_len}' could not be parsed by eval_expression()", arg_type="ERROR")
        return None
    if l_len == 0:
        log_print("arg_len is 0. This is very strange.", arg_debug, arg_type="WARNING")
        return bytes()
    if l_len > 0x400:
        log_print(f"arg_len is VERY large: {_hex_str_if_int(l_len)}. This is very strange.", arg_debug, arg_type="WARNING")

    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    l_bytes: bytes = _ida_bytes.get_bytes(l_addr, l_len)
    if arg_debug:
        l_parsed_hex = " ".join(hex_parse(l_bytes))
        log_print(f"arg_ea = 0x{l_addr:x}, arg_len = 0x{l_len:x} resulted in '{l_parsed_hex}'", arg_debug)
    return l_bytes

get_bytes = read_bytes

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def write_bytes(arg_ea: EvaluateType, arg_buf: Union[BufferType, int], arg_debug: bool = False) -> bool:
    ''' Write bytes (or hex string) to the IDB. OBS! The IDB might not match the file on disk or in active memory.
    Use ida_bytes.get_original_byte() to get back the bytes
    Replacement for ida_bytes.put_bytes() and ida_bytes.patch_bytes()
    '''
    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return False

    if isinstance(arg_buf, int):
        if arg_buf <= 0xFF: # allow ints that is <= 1 Byte to be handled as the user probably wanted
            l_buf: bytes = bytes.fromhex(f"{arg_buf:02x}")
        else:
            log_print(f'arg_buf is an int: {_hex_str_if_int(arg_buf)} but I need a buffer to write. (I actually am OK with a byte <= 0xFF also)', arg_type="ERROR")
            return False
    elif isinstance(arg_buf, bytes):
        l_buf = arg_buf
    else:
        l_temp = hex_parse(arg_buf, arg_debug=arg_debug)
        if l_temp is None:
            log_print("hex_parse() failed.", arg_type="ERROR")
            return False
        parsed_hex: str = " ".join(l_temp)
        log_print(f"addr: {l_addr:x}, bytes: {parsed_hex}", arg_debug)
        l_buf = bytes.fromhex(parsed_hex)
    _ida_bytes.patch_bytes(l_addr, l_buf)
    l_written_bytes = read_bytes(l_addr, len(l_buf), arg_debug=arg_debug)
    res = l_written_bytes == l_buf
    _ida_kernwin.request_refresh(_ida_kernwin.IWID_ALL, res) # Update the GUI if we actually managed to write something
    return res

set_bytes = patch_bytes = write_bytes

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def write_string(arg_ea: EvaluateType, arg_string: str, arg_append_NULL_byte: bool = True, arg_debug: bool = False) -> bool:
    ''' Write a null-terminated C string (UTF-8) to IDB'''
    return write_bytes(arg_ea=arg_ea, arg_buf=bytes(arg_string + ('\x00' if arg_append_NULL_byte else ''), encoding='utf-8'), arg_debug=arg_debug)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def import_h_file(arg_h_file: str, arg_flags: int = _ida_typeinf.PT_FILE, arg_debug: bool = False) -> bool:
    ''' Import a header file (.h file) with types into IDA. Same as using the menu File -> Load file -> Parse C header file. Default keybinding for the menu is Ctrl + F9

    Replacement for ida_typeinf.idc_parse_types() and ida_typeinf.parse_decls() '''
    if not os.path.exists(arg_h_file):
        log_print(f"File does not exists: '{arg_h_file}'", arg_type="ERROR")
        return False

    l_idc_parse_types_res = _ida_typeinf.idc_parse_types(arg_h_file, arg_flags)
    log_print(f"_ida_typeinf.idc_parse_types() result: {l_idc_parse_types_res}", arg_debug)

    res = 0 == l_idc_parse_types_res
    if not res:
        log_print(f"There where errors when trying to import the header file '{arg_h_file}'. Please make sure it's correct by manual load with Ctrl + F9", arg_type="ERROR")
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _local_types_as_c_types(arg_debug: bool = False) -> Optional[List[str]]:
    ''' Internal function. Get all local types as a list of strings that can be exported to a header file.
    Read more at <https://github.com/idapython/src/blob/ae62cd4df534f18c8c3dc47bd159d50c9822d82d/python/idc.py#L5142>
    '''
    class CustomPrinter(_ida_typeinf.text_sink_t):
        ''' Handle the _print calls by putting them into a list '''
        @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
        def __init__(self):
            _ida_typeinf.text_sink_t.__init__(self)
            self.lines: List[str] = [] # type: ignore[annotation-unchecked]

        @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
        def _print(self, arg_str: str): # IDA BUG: community_base.py:2008:8: W0237: Parameter 'str' has been renamed to 'arg_str' in overriding 'CustomPrinter._print' method (arguments-renamed)
            self.lines.append(arg_str)
            return 0

    l_printer = CustomPrinter()
    l_flags: int = 0
    l_flags |= _ida_typeinf.PDF_INCL_DEPS
    l_flags |= _ida_typeinf.PDF_DEF_FWD
    l_type_info_library_of_local_types: _ida_typeinf.til_t = _ida_typeinf.get_idati()
    res_of_print_decls: int = _ida_typeinf.print_decls(l_printer, l_type_info_library_of_local_types, [], l_flags )
    if res_of_print_decls > 0:
        log_print(f'Exported {res_of_print_decls} types', arg_debug)
    else:
        log_print('ida_typeinf.print_decl() failed', arg_type="ERROR")
        return None

    return l_printer.lines

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def export_h_file(arg_h_file: str = input_file.idb_path + ".h", arg_add_comment_at_top: bool = True, arg_debug: bool = False) -> str:
    ''' Export all local types into a header file

        @param arg_h_file The destination file
        @param arg_add_comment_at_top Add a comment field with some info about the file the header file was exported from

        Replacement for ida_typeinf.print_decls()
    '''
    l_local_types: Optional[List[str]] = _local_types_as_c_types(arg_debug=arg_debug)
    if l_local_types is None:
        log_print('_local_types_as_c_types() failed.', arg_type="ERROR")
        return "<<< Export header file failed >>>"

    with open(arg_h_file, "w", encoding="UTF-8", newline="\n") as f:
        if arg_add_comment_at_top:
            l_header_dict: Dict[str, str] = {}
            l_header_dict["generated_by"] = f"{__name__}.py version {__version__}"
            l_header_dict["generated_at"] = _timestamped_line('').strip()
            l_header_dict["input_filename"] = os.path.basename(input_file.filename)
            l_header_dict["MD5"] = input_file.md5
            l_header_dict["SHA256"] = input_file.sha256
            f.write("/*\n")
            f.write(json.dumps(l_header_dict, ensure_ascii=False, indent=4, default=str))
            f.write("\n*/")
        f.write("\n".join(l_local_types))

    return arg_h_file

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def string_encoding(arg_ea: EvaluateType, arg_detect: bool = False, arg_debug: bool = False) -> Optional[str]:
    '''
    Gets teh encoding of a string, can also be used to check if IDA thinks there is a string on that address
    If it's not and you want to make a string at that place, you can use string(<address>, arg_type="<encoding>", arg_create_string=True)

    @return: The encoding name, if there is no string on that address, then we return "" (empty str)

    Replacement for ida_bytes.is_strlit()
    '''
    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    l_is_str_lit = _ida_bytes.is_strlit(_idaapi_get_flags(l_addr, arg_debug=arg_debug))
    log_print(f"{arg_ea} is string literal: {l_is_str_lit}", arg_debug)
    if l_is_str_lit:
        res = _idaapi_encoding_from_strtype(_ida_nalt.get_str_type(l_addr))
    elif arg_detect:
        l_bytes = b''
        for i in range(0x30):
            l_byte = read_bytes(l_addr + i, 0x01)
            if l_byte is None:
                return None
            if l_byte == b'\x00':
                break
            l_bytes += l_byte

        log_print(f"chardet.detect({str(l_bytes)}) len: {len(l_bytes)}", arg_debug)
        l_detected = chardet.detect(l_bytes)
        log_print(f"chardet gave the following: {str(l_detected)}", arg_type="ERROR")
        res = l_detected["encoding"] if l_detected["encoding"] is not None else ""
    else:
        log_print(f"IDA does _NOT_ think there is a string at {_hex_str_if_int(arg_ea)} but you can try to detect what encoding is used by calling string_encoding(<address>, arg_detect=True)", arg_type="ERROR")
        res = ""
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _is_invalid_strtype(arg_strtype: int) -> bool:
    ''' It's not clear what is ida_nalt.get_str_type() should return that is a valid strtype.
    I used to think that 0xFFFFFFFF was the constant but I have gotten cases where 0xFFFFFF00 is also returned
    '''
    return (arg_strtype >> 8) == 0xFFFFFF

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _validate_encoding_name(arg_encoding: str) -> str:
    ''' Try to normalize some encoding names.
     Maybe check against <https://docs.python.org/3.12/library/codecs.html#standard-encodings> ?
    '''
    arg_encoding = arg_encoding.lower()
    arg_encoding = arg_encoding.replace("-", "")

    if arg_encoding in ["latin1"]:
        res = "Latin1"
    elif arg_encoding in ["utf8"]:
        res = "UTF-8"
    elif arg_encoding in ["utf16", "utf16le", "ucs2"]:
        res = "UTF-16LE"
    elif arg_encoding in ["utf16be"]:
        res = "UTF-16BE"
    elif arg_encoding in ["utf32", "utf32le"]:
        res = "UTF-32LE"
    else:
        res = arg_encoding
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _encoding_to_strtype(arg_encoding: str, arg_debug: bool = False) -> int:
    ''' Internal function. Do not use directly.

    @return returns the str_type: int, returns -1 on error
    '''
    l_encoding: str = _validate_encoding_name(arg_encoding)
    l_encoding_index: int = _ida_nalt.add_encoding(l_encoding) # If the encoding exists, then return the index, else create it and return index.
    if l_encoding_index == -1:
        log_print(f'ida_nalt.add_encoding("{arg_encoding}") failed.', arg_type="ERROR")
        return -1
    log_print(f"Encoding index: {l_encoding_index}", arg_debug)
    res: int = _ida_nalt.make_str_type(0, l_encoding_index)
    log_print(f"l_strtype: {res}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_encoding_from_strtype(arg_strtype: int) -> str:
    ''' Wrapper around ida_nalt.encoding_from_strtype() that honors the type hints
    It does NOT return None (NULLPTR) if we send in an invalid index as the docstring say

    Tags: Community fix, IDA Bug
    '''
    # TODO: Check the arg_strtype for weird input
    return _ida_nalt.encoding_from_strtype(arg_strtype)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def string(arg_ea: EvaluateType,
           arg_encoding: Optional[Union[int, str]] = None,
           arg_len: EvaluateType = 0,
           arg_create_string: bool = False,
           arg_flags: int = _ida_bytes.ALOPT_IGNHEADS | _ida_bytes.ALOPT_IGNPRINT | _ida_bytes.ALOPT_IGNCLT,
           arg_debug: bool = False) -> Optional[str]:
    ''' Reads a string (excluding the NULL terminator) from the IDB that can handle C strings, wide strings (UCS2/UTF-16).
    If you want to force read a string use the functions c_string() or wide_string().

    @param arg_type: See ida_nalt.STRTYPE_* for valid values. If you give it a string, I use this as encoding name
    @param arg_flags: See  ida_bytes.ALOPT_* for valid values. Default: ida_bytes.ALOPT_IGNHEADS | ida_bytes.ALOPT_IGNPRINT | ida_bytes.ALOPT_IGNCLT
    ALOPT_IGNHEADS: Don't stop if another data item is encountered. Only the byte values will be used to determine the string length. If not set, a defined data item or instruction will truncate the string.
    ALOPT_IGNPRINT: Don't stop at non-printable codepoints, but only at the terminating character (or not unicode-mapped character (e.g., 0x8f in CP1252))
    ALOPT_IGNCLT:   Don't stop at codepoints that are not part of the current 'culture'; accept all those that are graphical (this is typically used used by user-initiated actions creating string literals.)

    Replacement for ida_bytes.get_strlit_contents() and idc.get_strlit_contents()

    Read more: <https://python.docs.hex-rays.com/namespaceida__bytes.html#aafc64f6145bfe2e7d3e49a6e1e4e217c>
    '''
    if isinstance(arg_ea, _idautils.Strings.StringItem):
        log_print("arg_ea is of type idautils.Strings.StringItem, I will use that info instead of rest of arguments", arg_debug)
        l_type: int = arg_ea.strtype
        arg_len = arg_ea.length
        arg_ea = arg_ea.ea


    l_t_len = eval_expression(arg_len, arg_debug=arg_debug)
    if l_t_len is None:
        log_print(f'eval_expression({arg_len}) failed', arg_type="ERROR")
        return None
    l_len: int = l_t_len
    del l_t_len

    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    if isinstance(arg_encoding, str):
        l_type = _encoding_to_strtype(arg_encoding)
        if l_type == -1:
            log_print(f'_encoding_to_strtype("{arg_encoding}") failed')
            return None
    elif isinstance(arg_encoding, int):
        l_type = arg_encoding

    if is_unknown(l_addr, arg_debug=arg_debug):
        log_print(f"address: {_hex_str_if_int(l_addr)} is tagged as unknown, trying to convert it to string", arg_debug)
        if arg_encoding is None:
            is_unicode: bool = _ida_bytes.create_strlit(l_addr, l_len, _ida_nalt.STRTYPE_C_16)
            if is_unicode:
                log_print(f"ida_bytes.create_strlit(0x{l_addr:x}, 0x{l_len:x}, ida_nalt.STRTYPE_C_16) OK", arg_debug)
            else:
                log_print(f"ida_bytes.create_strlit(0x{l_addr:x}, 0x{l_len:x}, ida_nalt.STRTYPE_C_16) failed. Trying with normal C string", arg_debug)
                _ida_bytes.create_strlit(l_addr, l_len, _ida_nalt.STRTYPE_C)
        else:
            _ida_bytes.create_strlit(l_addr, l_len, l_type)
        _ida_auto.auto_wait()

    if arg_encoding is None:
        l_type = _ida_nalt.get_str_type(l_addr)
    if _is_invalid_strtype(l_type):
        log_print(f"IDA doesn't think there is a string at this address. (0x{l_type:x} is not a valid string type).", arg_type="ERROR")
        l_item_head: int = _ida_bytes.get_item_head(l_addr)
        if l_addr != l_item_head:
            log_print(f"IDA thinks that the item starts at 0x{l_item_head:x} instead of 0x{l_addr:x} which you entered. Maybe that's a clue?", arg_type="ERROR")

        log_print("If you want to try and force read it, use the function c_string() or wide_string()", arg_type="ERROR")
        log_print(f'If you want to create a string at this place (same as pressing <a> in IDA), use string(0x{l_addr:x}, arg_type="<encoding>", arg_create_string=True)', arg_type="ERROR")
        return None

    if not l_len:
        log_print(f"Calling _ida_bytes.get_max_strlit_length(0x{l_addr:x}, '{_idaapi_encoding_from_strtype(l_type)}', {arg_flags})", arg_debug)
        l_len = _ida_bytes.get_max_strlit_length(l_addr, l_type, arg_flags)
        log_print(f"That resulted in a len: {l_len}", arg_debug)

    log_print(f"type: 0x{l_type:x} = '{_idaapi_encoding_from_strtype(l_type)}'. See _ida_nalt.STRTYPE_* for valid types", arg_debug)
    log_print(f"l_len: {l_len}", arg_debug)

    l_t_bytes_read = read_bytes(l_addr, l_len, arg_debug=arg_debug)
    if l_t_bytes_read is None:
        log_print(f"read_bytes({_hex_str_if_int(l_addr)}, 0x{l_len:x}) returned None", arg_type="ERROR")
        return None
    l_bytes_read: bytes = l_t_bytes_read
    try:
        res = l_bytes_read.decode(_idaapi_encoding_from_strtype(l_type))
        log_print(f'l_bytes_read.decode({_idaapi_encoding_from_strtype(l_type)}) OK!', arg_debug)
    except:
        l_bytes_read = _ida_bytes.get_strlit_contents(l_addr, l_len, l_type)
        res = l_bytes_read.decode(_idaapi_encoding_from_strtype(l_type))
        if not res:
            log_print('l_bytes_read.decode() failed', arg_type="ERROR")
            return None

    if not res:
        log_print("Everything failed :-(", arg_type="ERROR")
        return None

    if arg_create_string:
        l_temp = _ida_bytes.create_strlit(l_addr, l_len, l_type)
        log_print(f"_ida_bytes.create_strlit(0x{l_addr:x}, {l_len}, {l_type}) --> {l_temp}", arg_debug)

    res = res.rstrip('\x00') # Remove the NULL terminator
    log_print(f"res: '{res}'", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def c_string(arg_ea: EvaluateType, arg_len: int = 0, arg_flags: int = _ida_bytes.ALOPT_IGNHEADS | _ida_bytes.ALOPT_IGNPRINT | _ida_bytes.ALOPT_IGNCLT, arg_debug: bool = False) -> Optional[str]:
    ''' Forcefully read the data as a NULL terminated C string (in UTF-8) For more info about the flags, see the docstring for string() '''
    return string(arg_ea=arg_ea, arg_encoding=_ida_nalt.STRTYPE_C, arg_len=arg_len, arg_flags=arg_flags, arg_debug=arg_debug)

utf8_string = string_utf8 = c_string

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def wide_string(arg_ea: EvaluateType, arg_len: int = 0, arg_flags: int = _ida_bytes.ALOPT_IGNHEADS | _ida_bytes.ALOPT_IGNPRINT | _ida_bytes.ALOPT_IGNCLT, arg_debug: bool = False) -> Optional[str]:
    ''' Forcefully read the data as a NULL terminated wide/unicode/UTF-16/UCS-2 string. For more info about the flags, see the docstring for string() '''
    return string(arg_ea=arg_ea, arg_encoding=_ida_nalt.STRTYPE_C_16, arg_len=arg_len, arg_flags=arg_flags, arg_debug=arg_debug)

utf16_string = string_utf16 = wide_string

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def strings(arg_only_first: int = 100000, arg_debug: bool = False) -> List[Tuple[int, int, str, str, int]]:
    ''' Returns all strings that IDA has found.
    The result is a list with tuples: (address: int, length: int, encoding: str, content: str, _ida_nalt.STRTYPE_*: enum)

    @param arg_only_first: Only get the first X entries
    '''

    res = []
    for string_item in _idautils.Strings():
        l_string_content: Optional[str] = string(string_item, arg_encoding=string_item.strtype, arg_debug=arg_debug)
        if l_string_content is None:
            l_string_content = f"<<< Could not read string at 0x{string_item.ea:x} >>>"
        res.append((string_item.ea, string_item.length, _idaapi_encoding_from_strtype(string_item.strtype), l_string_content, string_item.strtype))
        log_print(f'Found string: {l_string_content}', arg_debug)
        arg_only_first -= 1
        if arg_only_first < 1:
            break
    log_print(f"len(res) = {len(res)}", arg_debug)
    return res

def _strings_profiled():
    r''' Internal function. Do not use.
    Profile code to see what is taking most time
    From the command console: snakeviz C:\temp\strings.prof
    '''
    import cProfile
    import pstats

    profiler = cProfile.Profile()
    profiler.enable()

    a = strings()
    log_print(str(a))

    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats()
    stats.dump_stats(r'C:\temp\strings.prof')

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def pointer_type(arg_type_or_function_name: Union[str, _ida_typeinf.tinfo_t], arg_debug: bool = False) -> Optional[_ida_typeinf.tinfo_t]:
    ''' Send in a name or a type and get a pointer type back.
     Usually one use str(res) to get it as a string
    '''

    l_type: Optional[_ida_typeinf.tinfo_t] = arg_type_or_function_name if isinstance(arg_type_or_function_name, _ida_typeinf.tinfo_t) else get_type(arg_type_or_function_name, arg_debug=arg_debug)
    if l_type is None:
        log_print(f"get_type({arg_type_or_function_name}) failed", arg_type="ERROR")
        return None
    res = _ida_typeinf.tinfo_t()
    res.create_ptr(l_type)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _fix_assembly(arg_assembly_string: str, arg_debug: bool = False) -> str:
    ''' Internal function. If you read assembly from IDA and try to reassemble it, it won't work.
    OBS! This is NOT a complete fix!
    '''
    res = arg_assembly_string
    res = res.replace(" loc_", " 0x")
    res = res.replace(" near ", " ")
    res = res.replace(" short ", " ")
    res = res.replace(" near ptr ", " ")
    res = res.replace(" offset ", " ")
    res = res.replace(" large ", " ")
    res = res.replace(" ds:", " ")
    res = re.sub(r"([cdfg])s:(\d+)", r"\1s:[\2]", res, flags=re.IGNORECASE)
    res = re.sub(r"0x([0-9a-f]+)", r"\1h", res, flags=re.IGNORECASE) # Convert C style hex to asm style: 0x12 -> 12h
    res = res.replace("  ", " ")
    res = res.replace("  ", " ")
    res = res.replace("  ", " ")
    res = res.replace("  ", " ")
    log_print(f"in: {arg_assembly_string} --> out: {res}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def assemble(arg_ea: EvaluateType,
             arg_line: str,
             arg_cs: Optional[int] = None,
             arg_ip: Optional[int] = None,
             arg_code_is_32_bit: bool = True,
             arg_keep_size: bool = False,
             arg_debug: bool = False) -> Optional[int]:
    ''' Replacement for ida_idp.assemble() and idautils.Assemble() that has the "not interesting arguments" set to default + add the argument to keep the size of the instruction
        WARNING! IDA does NOT support 64-bit code! Only 32-bit and 16-bit!

        This function is not tested properly and is left "as is" since IDA does _NOT_ support 64-bit code

        @return The address after the one we assembled, this is so we can use to it in a loop

    '''
    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    if arg_ip is None:
        _t_segment = segment(l_addr, arg_debug=arg_debug)
        if _t_segment is None:
            log_print("segment() failed", arg_type="ERROR")
            return None
        arg_ip = l_addr - (_ida_segment.sel2para(_t_segment.sel) << 4) # This is how idautils.Assemble() does it. I have no idea what is happening here.

    NOP = "90" # x64/x86 only
    if arg_keep_size:
        l_ins = instruction(l_addr)
        if l_ins is None:
            log_print(f"instruction({_hex_str_if_int(l_addr)}) failed", arg_type="ERROR")
            return None
        instr_size_before = l_ins.size
        original_bytes = _ida_bytes.get_bytes(l_addr, 15)

    fixed_asm = _fix_assembly(arg_line, arg_debug=arg_debug) # IDA can't run assemble() on it's own code from it's own disassembly
    log_print(f"addr: {l_addr:x}, arg_line: '{arg_line}', fixed: '{fixed_asm}', arg_keep_size: {arg_keep_size}", arg_debug)

    if arg_cs is None:
        l_seg = segment(l_addr, arg_debug=arg_debug)
        if l_seg is None:
            log_print(f"segment({_hex_str_if_int(l_addr)}) failed", arg_type="ERROR")
            return None
        arg_cs = l_seg.sel

    log_print(f"_ida_idp.assemble(0x{l_addr:x}, arg_cs={arg_cs}, arg_ip=0x{arg_ip:x}, arg_code_is_32_bit={arg_code_is_32_bit}, line={fixed_asm})", arg_debug)
    if not _ida_idp.assemble(l_addr, arg_cs, arg_ip, arg_code_is_32_bit, fixed_asm): # _ida_idp.assemble can NOT assemble 64-bit code!
        log_print(f"_ida_idp.assemble(0x{l_addr:x}, arg_cs = {arg_cs}, arg_ip = 0x{arg_ip:x}, arg_code_is_32_bit = {arg_code_is_32_bit}, line = '{fixed_asm}') failed!", arg_type="ERROR")
        return None

    l_ins = instruction(l_addr)
    if l_ins is None:
        log_print(f"instruction({_hex_str_if_int(l_addr)}) failed", arg_type="ERROR")
        return None
    instr_size_after = l_ins.size

    log_print(f"_ida_idp.assemble() OK! instr_size_after: {instr_size_after}", arg_debug)
    if arg_keep_size:
        log_print(f"Before: {instr_size_before} -> after: {instr_size_after}", arg_debug)
        if instr_size_after == instr_size_before:
            log_print("Same size", arg_debug)
        elif instr_size_after < instr_size_before:
            log_print("Patching with NOPs", arg_debug)
            _ida_bytes.patch_bytes(l_addr + instr_size_after, bytes(bytearray.fromhex(NOP * (instr_size_before - instr_size_after))))
        else:
            # ERROR! The new code is too big, restore the original code and return an error
            log_print("Code too large", arg_type="ERROR")
            _ida_bytes.patch_bytes(l_addr, original_bytes)
            return None
    return l_addr + instr_size_after

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def disassemble(arg_ea: EvaluateType,
                arg_flags: int = _ida_lines.GENDSM_FORCE_CODE,
                arg_show_size: bool = True,
                arg_show_bytes: bool = True,
                arg_debug: bool = False) -> Optional[str]:
    ''' Disassemble bytes at the given address into assembly string. If you want an object, use ```instruction()``` instead

        @param arg_flags Default to ida_lines.GENDSM_FORCE_CODE. Read more: <https://python.docs.hex-rays.com/namespaceida__lines.html#a8fba3e94325a73b051a886d780262fe2>

        Replacement for idc.generate_disasm_line() and ida_lines.generate_disasm_line()
    '''
    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    l_text = _ida_lines.generate_disasm_line(l_addr, arg_flags)
    if not l_text:
        log_print(f"ida_lines.generate_disasm_line(0x{l_addr:x}, {arg_flags}) failed!", arg_type="ERROR")
        return None

    res = _ida_lines.tag_remove(l_text).lower()
    l_ins = instruction(l_addr, arg_debug=arg_debug)
    if l_ins is None:
        log_print(f"instruction({_hex_str_if_int(l_addr)}) failed", arg_type="ERROR")
        return None
    if arg_show_size:
        res += f' ; size: 0x{l_ins.size:x}'
    if arg_show_bytes:
        res += ' ; bytes: ' + " ".join(f"{b:02x}" for b in _instruction_to_bytes(l_ins)) # type: ignore[union-attr]
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def instruction(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[_ida_ua.insn_t]:
    '''
    Instruction object at given ea (Effective Address).

    Replacement for ida_ua.decode_insn()
    '''
    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None
    insn = _ida_ua.insn_t()
    _ida_ua.decode_insn(insn, l_addr)
    if insn.size == 0:
        log_print(f"Instruction is NOT valid at {_hex_str_if_int(l_addr)}", arg_type="ERROR")
        return None
    return insn

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def instruction_before(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[_ida_ua.insn_t]:
    ''' Returns the instruction before the given instruction '''
    return instruction(arg_ea=_ida_bytes.get_item_head(address(arg_ea, arg_debug=arg_debug) - 1), arg_debug=arg_debug)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def instruction_after(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[_ida_ua.insn_t]:
    ''' Returns the instruction after the given instruction '''
    return instruction(arg_ea=_ida_bytes.get_item_end(address(arg_ea, arg_debug=arg_debug) + 1), arg_debug=arg_debug)

def xrefs_to(arg_ea: EvaluateType, arg_debug: bool = False) -> Dict[int, _ida_xref.xrefblk_t]:
    ''' Replacement for idautils.XrefsTo()

    OBS! I add the member "type_name" to the objects returned in the dict
    @return Dict[address: int] --> _ida_xref.xrefblk_t
    '''
    res = {}
    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    for l_xref_to in _idautils.XrefsTo(l_addr):
        l_xref_to.type_name = _idautils.XrefTypeName(l_xref_to.type) # Add the type as a human readable string also. There is some black magic going on in _ida_xref.xrefblk_t.refs_from() where there are copying done
        res[l_xref_to.frm] = l_xref_to

    log_print(f"len of dict: {len(res)}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def pointer_size(arg_debug: bool = False) -> int:
    ''' Returns the native pointer size on the system in bytes '''

    l_type: Optional[_ida_typeinf.tinfo_t] = _parse_decl('void*', arg_debug=arg_debug)
    if l_type is None:
        log_print("_parse_decl('void*') returned None", arg_type="ERROR")
        return input_file.bits // 8
    res = l_type.get_size()
    log_print(f"Pointer size is {res}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def pointer(arg_ea: EvaluateType, arg_value: Optional[EvaluateType] = None, arg_debug: bool = False) -> Optional[int]:
    ''' Reads a pointer from memory. If no memory is active, then read from the IDB.
    If arg_value is set, then write that pointer to the memory. Works like WinDBG poi() '''

    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    if arg_value is not None:
        l_value: int = address(arg_value, arg_debug=arg_debug)
        if input_file.bits == 64:
            _ida_bytes.patch_qword(l_addr, l_value) # _ida_bytes.patch_qword() and _ida_bytes.patch_dword() returns False if the data you want to write is already on that place.
        elif input_file.bits == 32:
            _ida_bytes.patch_dword(l_addr, l_value)
        else:
            _ida_bytes.patch_word(l_addr, l_value)

    res = _ida_bytes.get_qword(l_addr) if input_file.bits == 64 else _ida_bytes.get_dword(l_addr) if input_file.bits == 32 else _ida_bytes.get_word(l_addr)
    return res
p = poi = ptr = pointer # WinDBG, I love you and I hate you

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def clipboard_copy(arg_text: EvaluateType, arg_debug: bool = False) -> bool:
    ''' Helper function to put text into the clipboard

    @return Returns True if we could put the text into the clipboard, False otherwise
    '''

    if not isinstance(arg_text, str):
        l_evaled: Optional[int] = eval_expression(arg_text, arg_debug=arg_debug)
        if l_evaled is None:
            log_print(f'eval_expression({arg_text}) returned None', arg_type="ERROR")
            return False
        l_text = f"0x{l_evaled:x}"
    else:
        l_text = arg_text
    log_print(f"We got length 0x{len(l_text):x} --> l_text: '{l_text}'", arg_debug)

    clipboard = QApplication.clipboard()
    clipboard.setText(l_text)
    return clipboard.ownsClipboard() and l_text == clipboard.text()

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_get_flags(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[int]:
    ''' Wrapper around ida_bytes.get_flags() '''
    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    return _ida_bytes.get_flags(l_addr)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def is_code(arg_ea: EvaluateType, arg_debug: bool = False) -> bool:
    ''' Is the given EA (Effective Address) code? '''
    l_flags = _idaapi_get_flags(arg_ea, arg_debug=arg_debug)
    if l_flags is None:
        log_print(f"_flags({_hex_str_if_int(arg_ea)}) returned None", arg_type="ERROR")
        return False
    return _ida_bytes.is_code(l_flags)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def is_data(arg_ea: EvaluateType, arg_debug: bool = False) -> bool:
    ''' Is the given EA (Effective Address) data? '''
    l_flags = _idaapi_get_flags(arg_ea, arg_debug=arg_debug)
    if l_flags is None:
        log_print(f"_flags({_hex_str_if_int(arg_ea)}) returned None", arg_type="ERROR")
        return False
    return _ida_bytes.is_data(l_flags)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def is_unknown(arg_ea: EvaluateType, arg_debug: bool = False) -> bool:
    ''' Is the given EA (Effective Address) unknown bytes? '''
    l_flags = _idaapi_get_flags(arg_ea, arg_debug=arg_debug)
    if l_flags is None:
        log_print(f"_flags({_hex_str_if_int(arg_ea)}) returned None", arg_type="ERROR")
        return False
    return _ida_bytes.is_unknown(l_flags)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def is_head(arg_ea: EvaluateType, arg_debug: bool = False) -> bool:
    ''' Is the given EA (Effective Address) an instruction OR data item? '''
    l_flags = _idaapi_get_flags(arg_ea, arg_debug=arg_debug)
    if l_flags is None:
        log_print(f"_flags({_hex_str_if_int(arg_ea)}) returned None", arg_type="ERROR")
        return False
    return _ida_bytes.is_head(l_flags)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def make_unknown(arg_ea: EvaluateType, arg_len: int = 1, arg_debug: bool = False) -> Optional[bool]:
    ''' Mark the bytes as unknown '''

    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    res = _ida_bytes.del_items(l_addr, _ida_bytes.DELIT_SIMPLE, arg_len)
    res &= _ida_auto.auto_wait() # waits for the auto analysis to be done. It returns True if everything went smooth and False if the user clicked cancel
    res &= is_unknown(l_addr, arg_debug=arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def make_code(arg_ea: EvaluateType, arg_len: int = 1, arg_force: bool = False, arg_debug: bool = False) -> Optional[bool]:
    ''' Tell IDA to parse the bytes at address as code.
    Replacement for ida_auto.auto_mark_range(a, b, ida_auto.AU_CODE), idc.auto_mark_range(a, b, ida_auto.AU_CODE) and idc.auto_make_code()
    '''

    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    if not arg_force:
        l_bytes = read_bytes(l_addr, 8)
        if l_bytes in (bytes.fromhex("0000000000000000"), bytes.fromhex("FFFFFFFFFFFFFFFF")):
            log_print(f"The address 0x{l_addr:x} does not seem to contain code. Use the argument arg_force=True to force the converstion", arg_type="WARNING")
            return False

    _ = make_unknown(l_addr, arg_len=arg_len, arg_debug=arg_debug) # _ida_ua.create_insn() needs to have clear bytes so we mark them as unknown before we make it code
    _ = _ida_ua.create_insn(l_addr)
    return _ida_auto.auto_wait() and is_code(l_addr, arg_debug=arg_debug) # _ida_auto.auto_wait() waits for the auto analysis to be done. It returns true if everything went smooth and false if the user clicked cancel

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def make_data(arg_ea: EvaluateType, arg_item_type: str = "BYTE", arg_number_of_items: int = 1, arg_debug: bool = False) -> Optional[bool]:
    ''' Make adress into data, can be used to create arrays also.

    Replacement for ida_bytes.create_data()
    '''
    l_addr = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None

    l_dataflag: int = _ida_bytes.stru_flag() # Default is a structure
    l_flags = {'BYTE': _ida_bytes.byte_flag(), 'WORD': _ida_bytes.word_flag(), 'DWORD': _ida_bytes.dword_flag(), 'QWORD': _ida_bytes.qword_flag()}
    if isinstance(arg_item_type, str):
        l_dataflag = l_flags.get(arg_item_type.upper(), _ida_bytes.stru_flag())

    l_type: Optional[_ida_typeinf.tinfo_t] = get_type(arg_item_type, arg_debug=arg_debug) # TODO: This is not working as expected on MIPS or other things that do not have a type named DWORD and such
    if l_type is None:
        log_print(f"Invalid arg_item_type, you wrote '{arg_item_type}'", arg_type="ERROR")
        return None

    l_type_id = _ida_netnode.BADNODE # If the dataflag is one of the data types in the data carusel, then we set this to ida_netnode.BADNODE
    if l_type.is_struct():
        l_type_id = _idc.get_struc_id(str(l_type))
        if l_type_id == _ida_idaapi.BADADDR:
            log_print(f"Cannot find any struct ID for '{arg_item_type}', make sure it's in the Local Types window", arg_type="ERROR")
            return None

    make_unknown(l_addr, arg_len=arg_number_of_items * l_type.get_size(), arg_debug=arg_debug) # _ida_bytes.create_data() needs to have unknown bytes so we mark them as unknown before we make it data
    log_print(f"Calling _ida_bytes.create_data(0x{l_addr:x}, 0x{l_dataflag:x}, {arg_number_of_items} * {l_type.get_size()}, 0x{l_type_id:x})", arg_debug)
    cd_res = _ida_bytes.create_data(l_addr, l_dataflag, arg_number_of_items * l_type.get_size(), l_type_id)
    if not cd_res:
        log_print(f"ida_bytes.create_data(0x{l_addr:x}, dataflag={l_dataflag}, size=0x{arg_number_of_items:x} * 0x{l_type.get_size():x}, tid=0x{l_type_id:x}) failed", arg_type="ERROR")
        return False
    return _ida_auto.auto_wait() and is_data(l_addr, arg_debug=arg_debug) # _ida_auto.auto_wait() waits for the auto analysis to be done. It returns true if everything went smooth and false if the user clicked cancel

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def make_array(arg_ea: EvaluateType, arg_item_type: str, arg_number_of_items: int, arg_debug: bool = False) -> Optional[bool]:
    ''' Make an array of item type with given length in number of items '''
    return make_data(arg_ea=arg_ea, arg_item_type=arg_item_type, arg_number_of_items=arg_number_of_items, arg_debug=arg_debug)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_parse_binpat_str(arg_out: _ida_bytes.compiled_binpat_vec_t, arg_ea: int, arg_in: str, arg_radix: int, arg_strlits_encoding: int = 0) -> bool:
    ''' Wrapper around ida_bytes.parse_binpat_str() which have a bad history of return type problems.
    Read more: <https://python.docs.hex-rays.com/namespaceida__bytes.html#a78f65e2beddbe9a9da023e022a6a6b06>

    Tags: Community fix, IDA Bug
    '''
    l_temp = _ida_bytes.parse_binpat_str(arg_out, arg_ea, arg_in, arg_radix, arg_strlits_encoding) # IDA 9.0 documentation say this is a bool but it STILL returns None on fail and '' (empty string) on success! WTF
    # log_print(f"ida_bytes.parse_binpat_str() have a bad history of type problems... type: {type(_t)}  value: '{_t}'", arg_debug)
    return l_temp == ""

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_bin_search(arg_start_ea: int, arg_end_ea: int, arg_data: _ida_bytes.compiled_binpat_vec_t, arg_flags: int) -> int:
    ''' Wrapper around bin_search() that actually honors the type hints
    @param start_ea: linear address, start of range to search
    @param end_ea: linear address, end of range to search (exclusive)
    @param data: the prepared data to search for (see parse_binpat_str())
    @param flags: combination of ida_bytes.BIN_SEARCH_* flags

    @return: the address of a match, or ida_idaapi.BADADDR if not found

    Tags: community fix, IDA bug
    '''
    l_temp = _ida_bytes.bin_search(arg_start_ea, arg_end_ea, arg_data, arg_flags)
    res = l_temp[0] if isinstance(l_temp, tuple) else l_temp # IDA 9.0 returns a tuple, IDA < 9.0 returns int
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _idaapi_get_encoding_bpu_by_name(arg_encoding_name: str) -> int:
    ''' Wrapper around ida_nalt.get_encoding_bpu_by_name().
    Take a human readable string and get the width of each element. e.g. "UTF-8" -> 1, "UTF-16" -> 2, "UTF-32" -> 2
    However, ida_nalt.get_encoding_bpu_by_name() actually returns 1 even for encodings IDA does NOT recognize which is unexpected
    Some encodings seems to be wrong, like Big5 <https://en.wikipedia.org/wiki/Big5> which should return 2 (I think?)

    Read more: <https://hex-rays.com/blog/igor-tip-of-the-week-13-string-literals-and-custom-encodings>
    OBS! There is a part where they write "On Linux or macOS, run iconv -l to see the available encodings. Note: some encodings are not supported on all systems so your IDB may become system-specific."

    Tags: Community fix, IDA bug(?)
    '''
    # TODO: Make some basic validation on the arg_encoding_name?
    l_encoding: str =_validate_encoding_name(arg_encoding_name)
    return _ida_nalt.get_encoding_bpu_by_name(l_encoding) # TODO: the encoding is not validated, if you send in a weird string, the function returns 1. Why?

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def search_binary(arg_pattern: BufferType,
                  arg_min_ea: Optional[EvaluateType] = None,
                  arg_max_ea: Optional[EvaluateType] = None,
                  arg_use_idas_parser: bool = False,
                  arg_radix: int = 0x10,
                  arg_flags: int = _ida_bytes.BIN_SEARCH_FORWARD,
                  arg_strlits_encoding: Union[int, str] = _ida_bytes.PBSENC_DEF1BPU,
                  arg_max_hits: EvaluateType = 1,
                  arg_debug: bool = False) -> Optional[List[int]]:
    ''' Search for a binary pattern in the file and returns the first hit.
    To get all hits, set the argument arg_max_hits = 0

    @param arg_pattern can be hex string, string, bytes, or list of bytes
    @param arg_min_ea start the search from this address, if None then we start from the first byte we can reach
    @param arg_max_ea end search if we pass this address, if None then we end from the last byte we can reach
    @param arg_use_idas_parser IDA has a special format that is used in the GUI and in their internal API. If you want to use that search type, set this to True
    If this flag is set, then I won't parse the input and just pass it to ida_bytes.parse_binpat_str(). See help(ida_bytes.parse_binpat_str)
    <https://python.docs.hex-rays.com/namespaceida__bytes.html#a78f65e2beddbe9a9da023e022a6a6b06>
    Use this flag if you like to search for byte sequences like "FF ?? ?? 13" (using wildcards)

    @param arg_flags Default: _ida_bytes.BIN_SEARCH_FORWARD See _ida_bytes.BIN_SEARCH_* for different flags
    @param radix The radix the numerical values in the search pattern is parsed as. Default: 0x10 (hex)
    @param arg_strlits_encoding Default: ida_bytes.PBSENC_DEF1BPU. This is used to parse the literals in the string. e.g. '"CreateFileA"'
    Other values that can be used: ida_bytes.PBSENC_ALL (all encodings IDA know of) or if you send in a string like 'UTF-16', then I translate that with ida_nalt.get_encoding_bpu_by_name('UTF-16')
    @param arg_max_hits After we found this many hits, we return. Set to 0 for all hits

    @return List[address: int]: List of ints where the search matched or [] if not found, returns None if something failed
    '''
    # TODO: This function needs more testing
    # TODO: split into smaller parts
    l_strlits_encoding: int = _idaapi_get_encoding_bpu_by_name(arg_strlits_encoding) if isinstance(arg_strlits_encoding, str) else arg_strlits_encoding

    l_max_hits: Optional[int] = eval_expression(arg_max_hits, arg_debug=arg_debug)
    if l_max_hits is None:
        log_print('eval_expression(arg_max_hits) failed', arg_type="ERROR")
        return None

    if isinstance(arg_pattern, str) and '?' in arg_pattern:
        log_print("arg_pattern contains '?' (wildcards), then this function only works with IDAs parser -> arg_use_idas_parser = True", arg_debug)
        arg_use_idas_parser = True

    if isinstance(arg_pattern, str) and ((arg_pattern.startswith("'") and arg_pattern.endswith("'")) or (arg_pattern.startswith('"') and arg_pattern.endswith('"'))):
        arg_pattern = '"' + arg_pattern[1:-1] + '"' # IDA only understands " and not '
        log_print("String search only works in IDAs parser -> arg_use_idas_parser = True", arg_debug)
        arg_use_idas_parser = True

    if arg_use_idas_parser:
        if not isinstance(arg_pattern, str):
            log_print(f'arg_use_idas_parser == True --> arg_pattern must be of type str. It is of type: {type(arg_pattern)}', arg_type="ERROR")
            return None
        search_pattern: str = arg_pattern
    else:
        l_parsed_hex = hex_parse(arg_pattern, arg_debug=arg_debug)
        if not l_parsed_hex:
            log_print(f'arg_pattern: "{str(arg_pattern)}" could not be parsed as bytes in any meaningful way. If you want to search for a string, make sure to put " around the string', arg_type="ERROR")
            return None

        search_pattern = " ".join(l_parsed_hex)
    log_print(f"search_pattern: '{str(search_pattern)}'", arg_debug)
    l_binpat = _ida_bytes.compiled_binpat_vec_t()
    if not _idaapi_parse_binpat_str(l_binpat, 0, search_pattern, arg_radix, l_strlits_encoding):
        log_print(f"ida_bytes.parse_binpat_str() failed to parse your input. You gave me {' '.join(hex_parse(arg_pattern))} which I converted to {search_pattern}", arg_type="ERROR")
        return None

    l_min_ea = _ida_ida.inf_get_min_ea() if arg_min_ea is None else address(arg_min_ea, arg_debug=arg_debug)
    if l_min_ea == _ida_idaapi.BADADDR:
        l_min_ea = _ida_ida.inf_get_min_ea()

    if isinstance(arg_max_ea, _ida_segment.segment_t):
        l_max_ea = arg_max_ea.end_ea - 1
    else:
        l_max_ea = _ida_ida.inf_get_max_ea() if arg_max_ea is None else address(arg_max_ea, arg_debug=arg_debug)
    if l_max_ea == _ida_idaapi.BADADDR:
        l_max_ea = _ida_ida.inf_get_max_ea()

    res: List[int] = []
    l_start_next_search_at = l_min_ea
    while True:
        l_start_next_search_at = _idaapi_bin_search(l_start_next_search_at, l_max_ea, l_binpat, arg_flags)
        if l_start_next_search_at == _ida_idaapi.BADADDR:
            break
        res.append(l_start_next_search_at)
        l_start_next_search_at += 1
        l_max_hits -= 1
        if l_max_hits == 0:
            break

    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def plugin_load_and_run(arg_plugin_name: str, arg_optional_argument_to_plugin: int = 0, arg_debug: bool = False) -> Optional[bool]:
    ''' Load a plugin and run it with optional argument.

    @param arg_plugin_name: The name of the plugin on disk in the IDA plugin folder or a full path to a .py file or full path to a .dll file
    @param arg_optional_argument_to_plugin: Each plugin has it's own way to handle arguments but often it's just 0.

    @return: Returns True or False depening on what the plugin returns. Returns None if the plugin cannot be found.

    Read more at <https://python.docs.hex-rays.com/namespaceida__loader.html#a1b29b29a91dceb429d7b85018303a92e>
    '''

    if os.path.sep not in arg_plugin_name:
        arg_plugin_name = os.path.splitext(arg_plugin_name)[0]

    log_print(f'Loading plugin: {arg_plugin_name}', arg_debug)
    _plugin = _ida_loader.load_plugin(arg_plugin_name)
    if not _plugin:
        log_print(f"Failed to load plugin '{arg_plugin_name}'", arg_type="ERROR")
        return None

    return _ida_loader.run_plugin(_plugin, arg_optional_argument_to_plugin)

load_and_run_plugin = plugin_load_and_run

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def segments() -> List[_ida_segment.segment_t]:
    ''' Get all segments in the program
    @return Returns List[segment_obj: ida_segment.segment_t]
    '''
    res = []
    for segment_index in range(_ida_segment.get_segm_qty()):
        res.append(_ida_segment.getnseg(segment_index))
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def segment(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[_ida_segment.segment_t]:
    ''' Gets the segment the given EA (Effective Address) '''
    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the IDB", arg_type="ERROR")
        return None
    res: Optional[_ida_segment.segment_t] = _ida_segment.getseg(l_addr)
    if not res:
        log_print(f"_ida_segment.getseg({_hex_str_if_int(l_addr)}) failed", arg_type="ERROR")
        return None

    log_print(f"Segment found: {str(res)}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _segment_permissions(arg_segment: EvaluateType,
                         arg_readable: Optional[bool] = None,
                         arg_writable: Optional[bool] = None,
                         arg_executable: Optional[bool] = None,
                         arg_debug: bool = False) -> int:
    ''' Internal function. To change a sections permissions, use:
    s = segment(<address>)
    s.writable = True

    Gets or sets the permission flags according to the arguments.
    If an argument is set to None, then it won't be changed.

    OBS! During an active debugger session, even if you set the executable flag,
    the memory will not be executable. This is only IDAs view and not what the OS thinks
    This is something I'm thinking of adding but atm I am just so tired of this function...

    '''
    # TODO: This function did not work as I expected, maybe time to remove it?
    l_segment: _ida_segment.segment_t = segment(arg_segment, arg_debug=arg_debug)

    MAX_MASK = 0xFFFFFFFFFFFFFFFF
    if arg_readable is not None:
        l_segment.perm = (~_ida_segment.SEGPERM_READ & MAX_MASK) & l_segment.perm            # Always clear the bit first
        l_segment.perm = l_segment.perm | (_ida_segment.SEGPERM_READ if arg_readable else 0) # Then set it if that what is we wanted

    if arg_writable is not None:
        l_segment.perm = (~_ida_segment.SEGPERM_WRITE & MAX_MASK) & l_segment.perm
        l_segment.perm = l_segment.perm | (_ida_segment.SEGPERM_WRITE if arg_writable else 0)

    if arg_executable is not None:
        l_segment.perm = (~_ida_segment.SEGPERM_EXEC & MAX_MASK) & l_segment.perm
        l_segment.perm = l_segment.perm | (_ida_segment.SEGPERM_EXEC if arg_executable else 0)

    return l_segment.perm

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def xref_add_code_ref(arg_from: EvaluateType, arg_to: EvaluateType, arg_flags: int = _ida_xref.XREF_USER | _ida_xref.fl_CN, arg_add_comment: bool = True, arg_debug: bool = False) -> Optional[bool]:
    ''' Creates a code xref arg_from --> arg_to.
    IDA does not show anything in the arg_from position so we add a comment at that address
    so we can follow the code xref both ways.

    arg_flags: int = ida_xref.XREF_USER | ida_xref.fl_CN. ida_xref.XREF_USER --> xref created by the user (and not IDA). ida_xref.fl_CN --> Flow: Call Near
    '''

    l_from_addr: int = address(arg_from, arg_debug=arg_debug)
    if l_from_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_from: '{_hex_str_if_int(arg_from)}' could not be located in the IDB", arg_type="ERROR")
        return None
    l_to_addr: int = address(arg_to, arg_debug=arg_debug)
    if l_to_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_to: '{_hex_str_if_int(arg_to)}' could not be located in the IDB", arg_type="ERROR")
        return None

    l_xref_res: bool = _ida_xref.add_cref(l_from_addr, l_to_addr, arg_flags) # Flags are _ida_xref.XREF_*
    if not l_xref_res:
        log_print(f"_ida_xref.add_cref(0x{l_from_addr:x}, 0x{l_to_addr:x}, {arg_flags}) failed", arg_type="ERROR")
        return False
    res = True
    if arg_add_comment:
        res = res and _comment_append(arg_ea=l_from_addr, arg_comment=f"code xref to: 0x{l_to_addr:x}", arg_debug=arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _decompiler_calls(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[List[_ida_hexrays.cexpr_t]]:
    ''' Internal function, use calls() instead.
    Returns a list of all _ida_hexrays.cexpr_t that is of type "call" '''
    res = []
    l_cfunc = decompile(arg_ea, arg_debug=arg_debug)
    if l_cfunc is None:
        log_print(f"Could not decompile '{_hex_str_if_int(arg_ea)}'", arg_type="ERROR")
        return None
    for item in l_cfunc.treeitems:
        if item.to_specific_type.opname == 'call':
            res.append(item.to_specific_type.cexpr)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _assembler_calls(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[List[_ida_ua.insn_t]]:
    ''' Internal function, use calls() instead.
    Returns a list of all _ida_ua.insn_t that is of type "call" '''
    res = []
    l_func = function(arg_ea, arg_debug=arg_debug)
    if l_func is None:
        log_print(f"Could not get a function object for '{_hex_str_if_int(arg_ea)}'", arg_type="ERROR")
        return None
    for l_address in l_func.code_items():
        if _ida_idp.is_call_insn(l_address):
            l_ins = instruction(l_address, arg_debug=arg_debug)
            res.append(l_ins)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def calls(arg_ea: EvaluateType, arg_use_assembly_calls_instead: bool = False, arg_debug: bool = False) -> Optional[Union[List[_ida_hexrays.cexpr_t], List[_ida_ua.insn_t]]]:
    ''' Return a list of all calls in the given function.
    This uses the decompiler but you can set arg_use_assembly_calls_instead=True to use the disassembler instead.

    Return: List[ida_hexrays.cexpr_t] is used as normal or List[_ida_ua.insn_t] if arg_use_assembly_calls_instead == True
    '''
    # TODO: Is this bad design to have different return types depending on arguments?
    return _decompiler_calls(arg_ea=arg_ea, arg_debug=arg_debug) if not arg_use_assembly_calls_instead else _assembler_calls(arg_ea=arg_ea, arg_debug=arg_debug)


# DATA TYPES ------------------------------------------------------------------------------------------------------------------


@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _fix_c_type(arg_c_type: str, arg_debug: bool = False) -> Optional[str]:
    '''
    Internal function. Please use get_type() instead.
    _ida_typeinf.parse_decl() is very strict on the format of the C type.

    Ex: mangled name "._ZdaPvm" --> demangled name "operator delete[](void *, unsigned long)" This will _ida_typeinf.parse_decl() not take
    '''
    if arg_c_type in ['byte', 'word', 'dword', 'qword']: # Some simple words that I use in lower case should be OK  # TODO: This is not true for things like MIPS
        return arg_c_type.upper() + ';'

    log_print(f"1st parse test is of: '{arg_c_type}'", arg_debug)
    _til = None
    _t = _ida_typeinf.tinfo_t()
    _ida_typeinf.parse_decl(_t, _til, arg_c_type, _ida_typeinf.PT_SIL) # PT_SIL == SILENT, meaning no popup that there were any problems
    if _t.is_well_defined():
        log_print(f"1st parse test OK! Returning '{arg_c_type}'", arg_debug)
        return arg_c_type

    # Ex: mangled name "._ZdaPvm" --> demangled name "operator delete[](void *, unsigned long)" --> IDA decompiler: "void __fastcall operator delete[](void *a1, unsigned __int64 a2);" This will _ida_typeinf.parse_decl() not take
    # However, it WILL parse the string "void __fastcall operator_delete__(void *a1, unsigned __int64 a2)"
    arg_c_type = arg_c_type.replace("operator ", "operator_")
    arg_c_type = arg_c_type.replace("[]", "__")

    # Mangled name:  "__int64 std__getline_char_std__char_traits_char__std__allocator_char__()" --> demangled: "std::istream & std::getline<char, std::char_traits<char>, std::allocator<char>>(std::istream &, std::string &, char)" -->
    # IDA prototype: "__int64 std::getline<char,std::char_traits<char>,std::allocator<char>>();" -- > IDA type: "__int64 std__getline_char_std__char_traits_char__std__allocator_char__()"
    arg_c_type = arg_c_type.replace(":", "_")
    arg_c_type = arg_c_type.replace("<", "_")
    arg_c_type = arg_c_type.replace(">", "_")

    # void __fastcall std__runtime_error___runtime_error(std::runtime_error *a1)


    arg_c_type = arg_c_type.replace(" *)", ")")
    arg_c_type += ';'
    arg_c_type = arg_c_type.replace(";;", ";")
    arg_c_type = arg_c_type.replace(";;", ";")

    log_print(f"2nd parse test is of: '{arg_c_type}'", arg_debug)
    _til = None
    _t = _ida_typeinf.tinfo_t()
    _ida_typeinf.parse_decl(_t, _til, arg_c_type, _ida_typeinf.PT_SIL) # PT_SIL == SILENT, meaning no popup that there were any problems
    if _t.is_well_defined():
        log_print(f"2nd parse test OK! Returning '{arg_c_type}'", arg_debug)
        return arg_c_type


    # This is ugly, I know...
    arg_c_type = arg_c_type.replace('__stdcall', '(__stdcall)').replace('((__stdcall))', '(__stdcall)')
    arg_c_type = arg_c_type.replace('__cdecl', '(__cdecl)').replace('((__cdecl))', '(__cdecl)')
    arg_c_type = arg_c_type.replace('__thiscall', '(__thiscall)').replace('((__thiscall))', '(__thiscall)')
    arg_c_type = arg_c_type.replace('__fastcall', '(__fastcall)').replace('((__fastcall))', '(__fastcall)')
    arg_c_type = arg_c_type.replace('__usercall', '(__usercall)').replace('((__usercall))', '(__usercall)')
    arg_c_type = arg_c_type.replace('__userpurge', '(__userpurge)').replace('((__userpurge))', '(__userpurge)')
    arg_c_type = arg_c_type.replace('__golang', '(__golang)').replace('((__golang))', '(__golang)')
    arg_c_type = arg_c_type.replace('__pascalcall', '(__pascalcall)').replace('((__pascalcall))', '(__pascalcall)')

    log_print(f"3rd parse test is of: '{arg_c_type}'", arg_debug)
    _t = _ida_typeinf.tinfo_t()
    _ida_typeinf.parse_decl(_t, _til, arg_c_type, _ida_typeinf.PT_SIL) # PT_SIL == SILENT, meaning no popup that there were any problems
    if _t.is_well_defined():
        return arg_c_type

    log_print("Failed to make the c type string into something IDA wants to swallow :-(", arg_debug, arg_type="ERROR")
    return None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _parse_decl(arg_c_type: str, arg_debug: bool = False) -> Optional[_ida_typeinf.tinfo_t]:
    ''' Internal function. Please use get_type() instead.
    Can convert a C string such as "int* a" to a ida_typeinf.tinfo_t (type information).
    To convert from tinfo_t --> str, use str(my_type).

    Replacement for ida_typeinf.parse_decl()
    '''
    # TODO: in linux the word 'dword' works but returns wrong type (size 0)
    log_print(f"arg_c_type before _fix_c_type(): '{arg_c_type}'", arg_debug)
    l_c_type: Optional[str] = _fix_c_type(arg_c_type, arg_debug=arg_debug)
    log_print(f"l_c_type after _fix_c_type(): {l_c_type}", arg_debug)
    if not l_c_type:
        log_print(f"_fix_c_type() failed. arg_c_type = '{l_c_type}'", arg_debug, arg_type="ERROR")
        return None

    res = _ida_typeinf.tinfo_t()
    _ida_typeinf.parse_decl(res, None, l_c_type, _ida_typeinf.PT_SIL) # PT_SIL == SILENT, meaning no popup that there were any problems
    if res.is_well_defined():
        log_print(f"Everything is OK, returning a ida_typeinf.tinfo_t with str: '{res}'", arg_debug)
        return res

    log_print(f"ida_typeinf.parse_decl(res, None, '{l_c_type}', ida_typeinf.PT_SIL) failed", arg_type="ERROR")
    return None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def get_type(arg_name_or_ea: Union[EvaluateType, _ida_hexrays.lvar_t, _ida_typeinf.tinfo_t],
             arg_cached_cfunc: Optional[_ida_hexrays.cfuncptr_t] = None,
             arg_debug: bool = False
             ) -> Optional[_ida_typeinf.tinfo_t]:
    ''' Get the type info from different inputs e.g.
    "_STARTUPINFOW" or
    "CreateFileA" or
    "0x00400000" or
    "char __stdcall(int a1, int a2, int a3)" or
    a register (if the debugger is running) that points to a an address where there is a type
    '''
    if isinstance(arg_name_or_ea, _ida_typeinf.tinfo_t):
        log_print("arg_name_or_ea is already a ida_typeinf.tinfo_t", arg_debug)
        return arg_name_or_ea

    if isinstance(arg_name_or_ea, _ida_hexrays.lvar_t):
        log_print(f"arg_name_or_ea is {type(arg_name_or_ea)} which have a function named 'type' that returns ida_typeinf.tinfo_t", arg_debug)
        return arg_name_or_ea.type()

    if hasattr(arg_name_or_ea, 'type') and isinstance(arg_name_or_ea.type, _ida_typeinf.tinfo_t):
        log_print(f"arg_name_or_ea is of type: {type(arg_name_or_ea)} which have a member called 'type' which is of type ida_typeinf.tinfo_t", arg_debug)
        return arg_name_or_ea.type

    # Are we sending in a parsable C type?
    if isinstance(arg_name_or_ea, str):
        log_print("arg_name_or_ea is a str, trying to convert it directly to a type", arg_debug)
        parsed_c_type = _parse_decl(arg_name_or_ea, arg_debug=arg_debug)
        if parsed_c_type is not None:
            return parsed_c_type
        log_print("Failed to parse it as a str", arg_debug)

    # Is the name we are looking for a function/label/name/register we can reach in our IDB?
    l_addr: int = address(arg_name_or_ea, arg_debug=arg_debug)
    if l_addr != _ida_idaapi.BADADDR:
        if not arg_cached_cfunc:
            arg_cached_cfunc = decompile(l_addr, arg_force_fresh_decompilation=True, arg_debug=arg_debug)

        if arg_cached_cfunc and arg_cached_cfunc.entry_ea == l_addr:
            l_function_prototype: str = function_prototype(arg_cached_cfunc, arg_cached_cfunc=arg_cached_cfunc)
            res = _parse_decl(l_function_prototype, arg_debug=arg_debug)
            log_print(f"address('{arg_name_or_ea}') --> 0x{l_addr:x}, function_prototype --> '{l_function_prototype}', 0x{l_addr:x} can be decompiled, so using the decompiled function prototype", arg_debug)
            if res:
                return res

        # TODO: Look up _ida_typeinf.idc_get_type and compare with _ida_typeinf.print_type
        l_print_type_flags: int = 0
        l_print_type_flags |= _ida_typeinf.PRTYPE_1LINE # Everything on 1 line
        l_print_type_flags |= _ida_typeinf.PRTYPE_SEMI  # Adds a ';' at the end
        l_type_at_addr = _ida_typeinf.print_type(l_addr, l_print_type_flags)
        if l_type_at_addr:
            res = _parse_decl(l_type_at_addr, arg_debug=arg_debug)
            log_print(f"print_type() --> '{res}'", arg_debug)
            return res

        log_print(f"Resolved to address: 0x{l_addr:x} but ida_typeinf.print_type() found no type there.", arg_type="ERROR")
        return None

    # Is the name a standard type in the IDA Type Information Library (TIL)?
    if not isinstance(arg_name_or_ea, str):
        log_print(f"arg_name_or_ea is not of any type I can parse. You sent me {type(arg_name_or_ea)}: {arg_name_or_ea}", arg_type="ERROR")
        return None

    o = _ida_typeinf.get_named_type(None, arg_name_or_ea, _ida_typeinf.NTF_TYPE) # Normal type such as structs and such in the standard Type Information Library (TIL)
    if not o:
        o = _ida_typeinf.get_named_type(None, arg_name_or_ea, _ida_typeinf.NTF_SYMU) # function (unmangled) use NTF_SYMM if you need a mangled name
    if not o:
        log_print(f"ida_typeinf.get_named_type('{arg_name_or_ea}') failed with both NTF_TYPE and NTF_SYMU", arg_type="ERROR")
        return None
    t = _ida_typeinf.tinfo_t()
    _code, type_str, fields_str, _cmt, field_cmts, _sclass, _value = o
    if t.deserialize(None, type_str, fields_str, field_cmts):
        log_print("t.deserialize() OK from a TIL", arg_debug)
        return t

    log_print("t.deserialize() failed", arg_type="ERROR")
    return None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def set_type(arg_original_type_name_or_ea: EvaluateType, arg_new_type: Union[str, _ida_typeinf.tinfo_t], arg_debug: bool = False) -> bool:
    ''' Set type by name or address.

    @param arg_original_type_name_or_ea:
    1. Known TIL name, e.g. SetFilePointer
    2. Address (or label) where the type should be set

    @param arg_new_type:
    1. cdecl string
    2. _ida_typeinf.tinfo_t
    3. address with a type at it
    4. label with a type at it
    5. Register pointing to an address type

    Replacement for ida_typeinf.apply_tinfo() and ida_typeinf.apply_cdecl() and ida_typeinf.set_symbol_type()
    '''

    l_new_type: Optional[_ida_typeinf.tinfo_t] = get_type(arg_new_type, arg_debug=arg_debug) if isinstance(arg_new_type, str) else arg_new_type
    if l_new_type is None:
        log_print("Failed to convert arg_new_type to ida_typeinf.tinfo_t'", arg_type="ERROR")
        return False

    l_addr = address(arg_original_type_name_or_ea, arg_debug=arg_debug)
    if l_addr != _ida_idaapi.BADADDR:
        log_print(f"{arg_original_type_name_or_ea} resolved to 0x{l_addr:x} which means I have to use ida_typeinf.apply_tinfo()", arg_debug)
        log_print(f"Calling _ida_typeinf.apply_tinfo(0x{l_addr:x}, '{l_new_type}', ida_typeinf.TINFO_DEFINITE)", arg_debug)
        make_unknown(l_addr, arg_debug=arg_debug) # The type system and the disassembly view can get out of sync. This hack makes sure that whatever was on that address before is now gone. # TODO: This will mess up functions?!
        if not _ida_typeinf.apply_tinfo(l_addr, l_new_type, _ida_typeinf.TINFO_DEFINITE):
            log_print("apply_tinfo() failed, this can happen but it still works...? IDA BUG?", arg_debug)
            l_type_now_temp = get_type(l_addr, arg_debug=arg_debug)
            if l_type_now_temp is None or l_type_now_temp != l_new_type:
                log_print("The type was NOT set correct :-(", arg_debug, arg_type="ERROR")
            else:
                log_print("The type was set correct even if apply_tinfo() returned False.", arg_debug)

        arg_original_type_name_or_ea = _ida_name.get_name(l_addr)
        if not arg_original_type_name_or_ea: # There is no symbol name at that address, then our work is done
            _ida_kernwin.request_refresh(_ida_kernwin.IWID_ALL)
            return True

    if arg_original_type_name_or_ea and isinstance(arg_original_type_name_or_ea, str): # This if is here is you send in a string that is both a label and a function type. ex. You change "GetProcAddress", that is both an imported function and a known (function) type name (TIL)
        arg_original_type_name_or_ea = arg_original_type_name_or_ea.replace("kernel32_", "")
        res = l_new_type.set_symbol_type(None, arg_original_type_name_or_ea, _ida_typeinf.NTF_REPLACE)       # If you call set_named_type() instead, then the local types will be created. The set_symbol_type() will set the TIL (for this IDB)
        log_print(f"Calling set_symbol_type() with arg_original_type_name_or_ea: '{arg_original_type_name_or_ea}' returned {'OK' if res == _ida_typeinf.TERR_OK else res}", arg_debug)
    else:
        log_print(f"'if arg_original_type_name_or_ea and isinstance(arg_original_type_name_or_ea, str)' failed. {type(arg_original_type_name_or_ea)} = '{arg_original_type_name_or_ea}'", arg_type="ERROR")
        return False

    res = _ida_typeinf.TERR_OK == res
    _ida_kernwin.request_refresh(_ida_kernwin.IWID_ALL, res)
    return res


# TODO: IDA 9.0 will break this by removing ida_typeinf.get_ordinal_qty written 2024-09-03
# @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
# def enum(arg_enum_name: Union[str, _ida_typeinf.tinfo_t], arg_debug: bool = False) -> Optional[str]:
    # ''' Takes a name of an enum that is in the IDB (can be seen in the local types window) and
        # returns the str of the enum as it would be seen in the local types edit enum window.

        # The result can be parsed by get_type() to get a tinfo_t
    # '''
    # if isinstance(arg_enum_name, _ida_typeinf.tinfo_t) and arg_enum_name.is_enum():
        # arg_enum_name = str(arg_enum_name)

    # if not isinstance(arg_enum_name, str):
        # log_print(f"arg_enum_name is {type(arg_enum_name)} but I expected str or _ida_typeinf.tinfo_t", arg_type="ERROR")
        # return None

    # l_local_til: _ida_typeinf.til_t = _ida_typeinf.get_idati() # docstring for get_idati(): Pointer to the local type library - this TIL is private for each IDB file
    # for ordinal in range(1, _ida_typeinf.get_ordinal_qty(l_local_til)+1):
        # ti = _ida_typeinf.tinfo_t()
        # if ti.get_numbered_type(l_local_til, ordinal) and ti.is_enum() and str(ti) == arg_enum_name:
            # res = f"enum {arg_enum_name}\n"
            # res += "{\n"
            # l_enum_type = _ida_typeinf.enum_type_data_t()
            # ti.get_enum_details(l_enum_type)
            # res += "\n".join(f"  {member.name} = 0x{member.value:x}, // {member.value}" for member in l_enum_type)
            # res += "\n}"
            # return res
    # log_print(f"Could not find any enum with the name '{arg_enum_name}'", arg_type="ERROR")
    # return None


# DEBUGGER ------------------------------------------------------------------------------------------------------------------


@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def debugger_refresh_memory_WARNING_VERY_EXPENSIVE() -> None:
    ''' Force a refresh of IDAs view on the targets memory.
    WARNING! This is a VERY expensive function
    Read more on refresh_debugger_memory: <https://python.docs.hex-rays.com/namespaceida__dbg.html#a6145474492fcf696e33d9ff1c8b86dfb>
    '''
    _ida_dbg.refresh_debugger_memory()
    return

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def debugger_is_running() -> bool:
    ''' Check if the debugger is running.
      @return Returns True if the debugger is running and False otherwise
    '''
    return _ida_dbg.is_debugger_on()

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def process_is_suspended() -> Optional[bool]:
    ''' Returns True if the debugger is active and the process is suspended.
        Returns False if the debugger is active but the process is not suspended.
        Returns None if debugger is not active
       '''
    if not debugger_is_running():
        log_print("You must have an active debugging session to use this function", arg_type="ERROR")
        return None

    return _ida_dbg.get_process_state() == _ida_dbg.DSTATE_SUSP

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _step_synchronous(arg_num_step_to_take: int = 1, arg_step_into: bool = True, arg_seconds_max_wait: int = 60, arg_debug: bool = False) -> Optional[int]:
    ''' The normal ida_dbg.step_into() / ida_dbg.step_over() is asynchronous which can make it a little tricky to use.
    @param arg_seconds_max_wait: number of seconds to wait, -1 --> infinity

    @return: event_id_t (if > 0) or dbg_event_code_t (if <= 0) of the LAST step
    See ida_dbg.wait_for_next_event() for the return value help.
    '''
    if not process_is_suspended():
        log_print("The process must be suspended. Use process_suspend() and to resume the process and to resume the process, use process_resume()", arg_type="ERROR")
        return None

    for _ in range(0, arg_num_step_to_take):
        if arg_step_into:
            _ida_dbg.step_into()
        else:
            _ida_dbg.step_over()
        res = _ida_dbg.wait_for_next_event(_ida_dbg.WFNE_SUSP, arg_seconds_max_wait)
        log_print(f"ida_dbg.wait_for_next_event() returned {res}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def step_into_synchronous(arg_num_step_to_take: int = 1, arg_seconds_max_wait: int = 60, arg_debug: bool = False) -> Optional[int]:
    ''' The normal ida_dbg.step_into() is asynchronous which can make it a little tricky to use.
    @param arg_seconds_max_wait: number of seconds to wait, -1 --> infinity

    @return: event_id_t (if > 0) or dbg_event_code_t (if <= 0) of the LAST step
    See ida_dbg.wait_for_next_event() for the return value help.

    read more: ida_dbg.wait_for_next_event(): <https://python.docs.hex-rays.com/namespaceida__dbg.html#a53d4d2d6a9426d06f758adea1cfeeee3>
    '''

    return _step_synchronous(arg_num_step_to_take=arg_num_step_to_take, arg_step_into=True, arg_seconds_max_wait=arg_seconds_max_wait, arg_debug=arg_debug)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def step_over_synchronous(arg_num_step_to_take: int = 1, arg_seconds_max_wait: int = 60, arg_debug: bool = False) -> Optional[int]:
    ''' The normal ida_dbg.step_over() is asynchronous which can make it a little tricky to use.
    @param arg_seconds_max_wait: number of seconds to wait, -1 --> infinity

    @return: event_id_t (if > 0) or dbg_event_code_t (if <= 0) of the LAST step
    See ida_dbg.wait_for_next_event() for the return value help.

    read more: ida_dbg.wait_for_next_event(): <https://python.docs.hex-rays.com/namespaceida__dbg.html#a53d4d2d6a9426d06f758adea1cfeeee3>

    '''
    return _step_synchronous(arg_num_step_to_take=arg_num_step_to_take, arg_step_into=False, arg_seconds_max_wait=arg_seconds_max_wait, arg_debug=arg_debug)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def breakpoint_add(arg_ea: EvaluateType,
                   arg_size: int = 0,
                   arg_breakpoint_type: int = _ida_idd.BPT_DEFAULT,
                   arg_condition: str = '',
                   arg_debug: bool = False) -> Optional[_ida_dbg.bpt_t]:
    ''' Add (set) a breakpoint (Software or Hardware)
        @param arg_type Set to ida_idd.BPT_WRITE or ida_idd.BPT_READ or ida_idd.BPT_WRITE to set hardware breakpoints
    '''
    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the process", arg_type="ERROR")
        return None

    if arg_breakpoint_type in [_ida_idd.BPT_READ, _ida_idd.BPT_WRITE, _ida_idd.BPT_EXEC] and arg_size == 0:
        log_print("Your arg_type is a hardware breakpoint but no size is given so I set arg_size to 1", arg_type="WARNING")
        arg_size = 1

    l_success: bool = _ida_dbg.add_bpt(l_addr, arg_size, arg_breakpoint_type)
    if not l_success:
        log_print(f"ida_dbg.add_bpt(0x{l_addr:x}, 0x{arg_size:x}, 0x{arg_breakpoint_type:x}) returned False. Maybe there is already a breakpoint there?", arg_type="ERROR")
        return None

    l_bpt = _ida_dbg.bpt_t()
    l_success = _ida_dbg.get_bpt(l_addr, l_bpt)
    if not l_success:
        log_print(f"ida_dbg.get_bpt(0x{l_addr:x}, l_bpt) returned False", arg_type="ERROR")
        return None

    if arg_condition:
        l_bpt.condition = arg_condition
    l_bpt.elang = 'Python'
    l_update_bpt = breakpoint_update(l_bpt)
    if not l_update_bpt:
        log_print("ida_dbg.update_bpt(l_bpt) returned False", arg_type="ERROR")
        return None
    return l_bpt

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def breakpoint_disable(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[bool]:
    ''' Disable a breakpoint '''
    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the process", arg_type="ERROR")
        return None

    return _ida_dbg.disable_bpt(l_addr)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def breakpoint_enable(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[bool]:
    ''' Enable a breakpoint '''
    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the process", arg_type="ERROR")
        return None

    return _ida_dbg.enable_bpt(l_addr)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def breakpoint_delete(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[bool]:
    ''' Delete a breakpoint '''

    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the process", arg_type="ERROR")
        return None

    return _ida_dbg.del_bpt(l_addr)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def breakpoint(arg_ea: EvaluateType, arg_create_if_needed: bool = False, arg_debug: bool = False) -> Optional[_ida_dbg.bpt_t]:
    ''' Get the breakpoint at the given address. If there is no breakpoint there, returns None
    @param arg_create_if_needed if there is no breakpoint, then create one at that address if this argument is set
    '''

    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"arg_ea: '{_hex_str_if_int(arg_ea)}' could not be located in the process", arg_type="ERROR")
        return None

    res = _ida_dbg.bpt_t()
    l_success: bool = _ida_dbg.get_bpt(l_addr, res)
    if not l_success and arg_create_if_needed:
        breakpoint_add(arg_ea=l_addr, arg_debug=arg_debug)
        l_success = _ida_dbg.get_bpt(l_addr, res)

    if not l_success:
        log_print(f"Could not get breakpoint at 0x{l_addr:x} (ida_dbg.get_bpt() returned False)", arg_type="ERROR")
        return None

    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def breakpoint_update(arg_breakpoint: _ida_dbg.bpt_t) -> bool:
    ''' Update (change) a breakpoint that already exists.
    OBS! You can NOT change the address (ea) of the breakpoint with this function!
    ida_dbg.update_bpt have a long docstring with potential problems, please read that.
    '''
    return _ida_dbg.update_bpt(arg_breakpoint)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def process_suspend() -> bool:
    ''' Passthru ida_dbg.suspend_process() '''
    return _ida_dbg.suspend_process()

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def process_resume() -> bool:
    ''' Passthru for ida_dbg.continue_process'''
    return _ida_dbg.continue_process()

process_continue = process_resume

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def process_options(arg_debug: bool = False) -> Dict[str, str]:
    ''' Get the options which the process is started '''
    (file_on_disk, program_arguments, directory, remote_server_ip, remote_server_password, remote_server_port) = _ida_dbg.get_process_options()
    res = {'file_on_disk': file_on_disk,
           'program_arguments' : program_arguments,
           'directory': directory,
           'remote_server_ip': remote_server_ip,
           'remote_server_password': remote_server_password,
           'remote_server_port': str(remote_server_port)}
    log_print(f"res: {res}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _add_property_to_registers_object(arg_reg_name: str, arg_debug: bool = False):
    ''' Internal function. For some strange reason, this line has to be in called from its own function. I don't know why and I have spent WAY TOO MUCH TIME on trying to figure out why... '''
    arg_reg_name = arg_reg_name.replace('$', '').lower() # MIPS
    setattr(_registers_object, arg_reg_name, property(fget=lambda self: registers._as_dict[arg_reg_name], fset=lambda self, value: _register(arg_reg_name, arg_set_value=value, arg_debug=arg_debug))) # type: ignore[arg-type] # To be honest, I don't understand what mypy is complaining about

class _registers_object():
    ''' Interface to interact with the registers. It works like idautils.cpu but my version supports tab completion.

        In general, you should not use this function but instead use the community_base.registers object
    '''
    _as_dict: Dict[str, _ida_idp.reg_info_t] = {}

    @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
    def __init__(self, arg_reg_sizes: Optional[List[int]] = None, arg_debug: bool = False):
        self._populate_register_dict(arg_reg_sizes=arg_reg_sizes, arg_debug=arg_debug)

    @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
    def _populate_register_dict(self, arg_reg_sizes: Optional[List[int]] = None, arg_debug: bool = False) -> Dict[str, _ida_idp.reg_info_t]:
        ''' Returns a dict that containts all registers in this processor module.
        The dict looks like: Dict[register_name: str] = register_info: _ida_idp.reg_info_t

        OBS! This function is realtively slow and if you just want a list of strings to check register names against then use
        'rax' in community_base.registers._as_dict

        Replacement for idautils.GetRegisterList() and _ida_idp.ph_get_regnames() which do NOT return a complete list. RAX is missing among many.
        '''
        self._as_dict = {}
        if arg_reg_sizes is None:
            arg_reg_sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256] # This is bytes

        if isinstance(arg_reg_sizes, int):
            arg_reg_sizes = [arg_reg_sizes]

        for reg_index in range(0, 500):
            for reg_size_in_bytes in arg_reg_sizes:
                reg_name: str = _ida_idp.get_reg_name(reg_index, reg_size_in_bytes) or "<no register name>"
                if reg_name in ['k0', 'k1', 'k2', 'k3', 'k4', 'k5', 'k6', 'k7', 'mxcsr', 'bnd0', 'bnd1', 'bnd2', 'bnd3', 'fpctrl', 'fpstat', 'fptags']: # Ignore these special registers
                    continue
                # log_print(f"_ida_idp.get_reg_name({reg_index}, {reg_size_in_bytes}): {reg_name}", arg_debug)
                reg_info = _ida_idp.reg_info_t()
                if _ida_idp.parse_reg_name(reg_info, reg_name) and reg_info.size == reg_size_in_bytes:
                    reg_name = reg_name.replace('$', '').lower() # MIPS
                    self._as_dict[reg_name] = reg_info
                    _add_property_to_registers_object(reg_name, arg_debug=arg_debug)
        return self._as_dict

    def __str__(self):
        _regs = [reg for reg in self._as_dict]
        _regs.sort()
        return ", ".join(_regs)

    def __repr__(self):
        return f"{type(self)} with the following registers:\n{str(self)}"

registers = _registers_object() # Recreated in the "_new_file_opened_notification_callback" function

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _new_file_opened_notification_callback(arg_nw_code: int, arg_is_old_database: int) -> None:
    ''' Callback that is triggered whenever a file is opened in IDA Pro.

    @param arg_nw_code: int is the event number that caused this callback.
    @param arg_is_old_database == 1 if there was an IDB/I64 and 0 if it's a new file
    '''
    del arg_nw_code # This is never used but needed in the prototype
    del arg_is_old_database # This is never used but needed in the prototype

    global registers
    registers = _registers_object()
    global input_file
    input_file = _input_file_object()
    log_print(f"{__name__} is (re)loaded", arg_type="INFO")
_ida_idaapi.notify_when(_ida_idaapi.NW_OPENIDB, _new_file_opened_notification_callback) # See also : NW_INITIDA, NW_REMOVE, NW_CLOSEIDB, NW_TERMIDA

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _add_links_to_docstring(arg_function: Callable, arg_link: str) -> None:
    ''' If there is no link the official documentation for the given function, add a link to to the official documentation '''
    l_docstring: str = getattr(arg_function, "__doc__")
    if "hex-rays.com" in l_docstring:
        # log_print(f"Function already has a link, ignoring", arg_type="WARNING")
        return

    setattr(arg_function, "__doc__", l_docstring + "\nRead more: " + arg_link)
    return

# Add links to the official documentation for some functions, more will be added
_add_links_to_docstring(_ida_nalt.get_ida_notepad_text, "https://python.docs.hex-rays.com/namespaceida__nalt.html#afbce150733a7444c14e83db7411cf3c9")
_add_links_to_docstring(_ida_dbg.refresh_debugger_memory, "https://python.docs.hex-rays.com/namespaceida__dbg.html#a6145474492fcf696e33d9ff1c8b86dfb")
_add_links_to_docstring(_ida_idp.process_config_directive, "https://python.docs.hex-rays.com/namespaceida__idp.html#a8f7be5936a3a9e1f1f2bc7e406654f38")
_add_links_to_docstring(_ida_kernwin.str2ea, "https://python.docs.hex-rays.com/namespaceida__kernwin.html#a08d928125a472cc31098defe54be7382")
_add_links_to_docstring(_ida_dbg.wait_for_next_event, "https://python.docs.hex-rays.com/namespaceida__dbg.html#a53d4d2d6a9426d06f758adea1cfeeee3")
_add_links_to_docstring(_ida_bytes.get_strlit_contents, "https://python.docs.hex-rays.com/namespaceida__bytes.html#aafc64f6145bfe2e7d3e49a6e1e4e217c")
_add_links_to_docstring(_ida_kernwin.execute_ui_requests, "https://python.docs.hex-rays.com/namespaceida__kernwin.html#a31cf8b9bf7e6ba055f92bb1c2e6a5858")
_add_links_to_docstring(_ida_kernwin.process_ui_action, "https://python.docs.hex-rays.com/namespaceida__kernwin.html#ab67f049dcd5c47b16f5230ebc3e71d1b")
_add_links_to_docstring(_ida_loader.load_and_run_plugin, "https://python.docs.hex-rays.com/namespaceida__loader.html#a1b29b29a91dceb429d7b85018303a92e")
_add_links_to_docstring(_ida_idaapi.notify_when, "https://python.docs.hex-rays.com/namespaceida__idaapi.html#a0b63655706845252b36a543e550d884e")
_add_links_to_docstring(_ida_dbg.update_bpt, "https://python.docs.hex-rays.com/namespaceida__dbg.html#a65a328849707f223bf166d0a8df5d695")

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _register(arg_register: Union[str, _ida_idp.reg_info_t], arg_set_value: Optional[EvaluateType] = None, arg_debug: bool = False) -> Optional[int]:
    ''' Internal function. The public interface is the community_base.registers.<register_name>
    Get or set the value in a register in a running process '''

    if not process_is_suspended():
        log_print("The process must be suspended to be able to read/write the register. Use process_suspend() and to resume the process, use process_resume()", arg_type="ERROR")
        return None

    if isinstance(arg_register, _ida_idp.reg_info_t):
        arg_register = _ida_idp.get_reg_name(arg_register.reg, arg_register.size)
        log_print(f"arg_register is of type ida_idp.reg_info_t, using that info to get the register name: '{arg_register}'", arg_debug)
    else:
        if arg_register not in registers._as_dict:
            log_print(f"arg_register: '{arg_register}' is not a valid register. These registers are support in this architecture:\n{str(registers)}", arg_type="ERROR")
            return None

    if arg_set_value is not None:
        log_print(f"Set value: {arg_set_value} will be checked by eval_expression()", arg_debug)
        l_expr_res: Optional[int] = eval_expression(arg_set_value, arg_debug=arg_debug)     # OBS! eval_expression() understands register names so _register('rax', 'rbx') has the effect: rax = rbx
        if isinstance(l_expr_res, int):
            _ida_dbg.set_reg_val(arg_register, l_expr_res)
        else:
            log_print(f"eval_expression('{arg_set_value}') returned None", arg_type="ERROR")
            return None
    res = None
    try:
        res = _ida_dbg.get_reg_val(arg_register)
        if isinstance(res, bytes):
            log_print("Registers such at xmm1 (and more) have return value that is of type bytes and not int)", arg_debug)
            res = int.from_bytes(res, 'little')

    except Exception as exc:
        log_print(f"res = ida_dbg.get_reg_val('{arg_register}') threw an exception:'", arg_type="ERROR")
        log_print(str(exc), arg_type="ERROR")
        return None
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def appcall(arg_function_name: EvaluateType,
            arg_prototype: Union[EvaluateType, _ida_typeinf.tinfo_t, None] = None,
            arg_set_type_in_IDB: bool = True,
            arg_debug: bool = False
            ) -> Optional[_ida_idd.Appcall_callable__]:
    ''' To easy call functions (Appcall) from the python code, this function can help you make it callable.
    Hexrays example code: <https://hex-rays.com/blog/practical-appcall-examples/>
    <https://docs.hex-rays.com/user-guide/debugger/debugger-tutorials/appcall_primer>

    @param arg_prototype can be either:
    c type string
    _ida_typeinf.tinfo_t
    address/name/label/register which can be resolved to a an address and then the type is read from that location.

    @param arg_set_type_in_IDB: Set the type at the function start in the IDB also

    If you are debugging and have a function you want to call:
    decrypt_function = appcall('this_is_the_decrypt_function')
    res = decrypt_function(0x00401000, 0x12) # The arguments here are whatever that function you are calling have
    print(res)

    Replacement for ida_idd.Appcall.proto()
    '''
    if not process_is_suspended():
        log_print("The process must be active and suspended to be able to use appcall. Use process_suspend() and to resume the process, use process_resume()", arg_type="ERROR")
        return None

    l_addr = address(arg_function_name, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"Could not find {arg_function_name}", arg_type="ERROR")
        return None

    l_function_prototype: Optional[_ida_typeinf.tinfo_t] = get_type(l_addr if arg_prototype is None else arg_prototype, arg_debug=arg_debug)
    if l_function_prototype is None:
        log_print(f"Failed to get a good type on'{_hex_str_if_int(l_addr)}'. Either set it with set_type() or pass the argument arg_prototype to this function.", arg_type="ERROR")
        return None

    if arg_set_type_in_IDB:
        set_type(l_addr, l_function_prototype, arg_debug=arg_debug)

    log_print(f"Calling ida_idd.Appcall.proto('{name(l_addr,arg_debug=arg_debug)}', '{l_function_prototype}')", arg_debug)
    res = _ida_idd.Appcall.proto(l_addr, l_function_prototype)
    res.__doc__ = l_function_prototype
    res.prototype = l_function_prototype
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def allocate_memory_in_target(arg_size: EvaluateType, arg_executable: bool = False, arg_debug: bool = False) -> Optional[int]:
    ''' If the debugger is running, try to allocate memory in target process.

    This function is using the Appcall magic in IDA, it can only be used in an active debugger session.
    It saves the current state and sets the arguments and then calls the function. After the function call is complete, IDA sets the state back to what it was before.
    To know where to set the arguments, the function must have a proper type. You can se how I use the function here under in my code.
    '''
    # TODO: Needs to be tested more
    # TODO: Split into different functions depending on OS?
    l_t_size = eval_expression(arg_size, arg_debug=arg_debug)
    if l_t_size is None:
        log_print(f"eval_expression({_hex_str_if_int(arg_size)}) failed", arg_type="ERROR")
        return None
    l_size: int = l_t_size
    if _ida_name.get_name_ea(_ida_idaapi.BADADDR, '__libc_malloc') != _ida_idaapi.BADADDR:                    # Linux
        # TODO: arg_executable is not working. Switch to mmap
        l_malloc = appcall('__libc_malloc', 'void *__fastcall(size_t size)', arg_debug=arg_debug)
        if l_malloc is None:
            log_print('Could not find __libc_malloc', arg_type="ERROR")
            return None

        res = l_malloc(l_size)
    elif _ida_name.get_name_ea(_ida_idaapi.BADADDR, 'kernelbase_VirtualAlloc') != _ida_idaapi.BADADDR:    # Windows
        MEM_COMMIT = 0x1000
        PAGE_READWRITE = 0x04
        PAGE_EXECUTE_READWRITE = 0x40
        l_kernelbase_VirtualAlloc = appcall('kernelbase_VirtualAlloc', 'PVOID __stdcall(PVOID lpAddress, SIZE_T dwSize, __int32 flAllocationType, __int32 flProtect)', arg_debug=arg_debug)
        if l_kernelbase_VirtualAlloc is None:
            log_print('Failed to find kernelbase_VirtualAlloc', arg_type="ERROR")
            return None
        res = l_kernelbase_VirtualAlloc(None, l_size, MEM_COMMIT, PAGE_EXECUTE_READWRITE if arg_executable else PAGE_READWRITE)

    elif input_file.format.startswith('ELF64'): # Linux x64 without GLIBC
        # TODO: arg_executable is not working I guess

        # If we can't find __libc_malloc on Linux64, we can simulate this with:
        # mmap(0, size, PROT_WRITE|PROT_READ, MAP_ANON|MAP_PRIVATE, -1, 0) -->
        # mmap(0, size, 3, 0x22, -1, 0)
        l_syscall_as_bytes = bytes.fromhex("0F 05")

        # TODO: This is only working on x64 atm

        # Save the state
        l_rip = registers.rip.value # type: ignore[attr-defined]
        l_rax = registers.rax.value # type: ignore[attr-defined]
        l_rdi = registers.rdi.value # type: ignore[attr-defined]
        l_rsi = registers.rsi.value # type: ignore[attr-defined]
        l_rdx = registers.rdx.value # type: ignore[attr-defined]
        l_r10 = registers.r10.value # type: ignore[attr-defined]
        l_r8 = registers.r8.value # type: ignore[attr-defined]
        l_r9 = registers.r9.value # type: ignore[attr-defined]

        # Setup the new state
        l_syscall_already_in_code: Optional[List[int]] = []
        for l_segment in segments():
            if l_segment.executable:
                l_syscall_already_in_code = search_binary(arg_pattern=l_syscall_as_bytes, arg_min_ea=l_segment.start_ea, arg_max_ea=l_segment.end_ea-2, arg_debug=arg_debug)
                if l_syscall_already_in_code is None:
                    log_print("search_binary(SYSCALL_AS_BYTES) failed", arg_type="ERROR")
                    return None
                if l_syscall_already_in_code != []:
                    log_print(f"Found SYSCALL at 0x{l_syscall_already_in_code[0]:x}", arg_debug)
                    registers.rip.value = l_syscall_already_in_code  # type: ignore[attr-defined]
                    break

        if l_syscall_already_in_code == []:
            log_print("Could NOT find SYSCALL so I have to create my own", arg_debug)
            l_t_ins = instruction(l_rip, arg_debug=arg_debug)
            if l_t_ins is None:
                return None
            l_len_of_instruction_before = len(l_t_ins)
            l_saved_bytes = read_bytes(l_rip, len(l_syscall_as_bytes), arg_debug=arg_debug)
            if l_saved_bytes is None:
                return None
            write_bytes(l_rip, l_syscall_as_bytes, arg_debug=arg_debug)
            make_code(l_rip, len(l_syscall_as_bytes), arg_debug=arg_debug)

        # syscall mmap == 9
        registers.rax.value = 9 # type: ignore[attr-defined]

        # Addr hint
        registers.rdi.value = 0 # type: ignore[attr-defined]

        # Size to allocate
        registers.rsi.value = l_size # type: ignore[attr-defined]

        # prot = PROT_WRITE | PROT_READ
        registers.rdx.value = 3 # type: ignore[attr-defined]

        # flags = MAP_ANON | MAP_PRIVATE
        registers.r10.value = 0x22 # type: ignore[attr-defined]

        # fd (file descriptor backing this memory mapping)
        registers.r8.value = -1 # type: ignore[attr-defined]

        # off
        registers.r9.value = 0 # type: ignore[attr-defined]

        step_over_synchronous(arg_seconds_max_wait=60, arg_debug=arg_debug)
        res = registers.rax.value # type: ignore[attr-defined]

        # Restore the old state
        if l_syscall_already_in_code == []:
            l_t_saved_bytes: bytes = l_saved_bytes # type: ignore[assignment] # mypy miss that it is ok, l_saved_bytes: bytes
            _ = write_bytes(l_rip, l_t_saved_bytes, arg_debug=arg_debug)
            _ = make_code(l_rip, max(l_len_of_instruction_before, len(l_t_saved_bytes)))

        registers.rip.value = l_rip # type: ignore[attr-defined]
        registers.rax.value = l_rax # type: ignore[attr-defined]
        registers.rdi.value = l_rdi # type: ignore[attr-defined]
        registers.rsi.value = l_rsi # type: ignore[attr-defined]
        registers.rdx.value = l_rdx # type: ignore[attr-defined]
        registers.r10.value = l_r10 # type: ignore[attr-defined]
        registers.r8.value = l_r8 # type: ignore[attr-defined]
        registers.r9.value = l_r9 # type: ignore[attr-defined]
    else:
        log_print("Could NOT find any function that allocates memory", arg_type="ERROR")
        return None

    debugger_refresh_memory_WARNING_VERY_EXPENSIVE()
    _ida_kernwin.request_refresh(_ida_kernwin.IWID_ALL)
    return eval_expression(res)

malloc = allocate_memory_in_target

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def modules(arg_name_filter_regex: str = ".*",  arg_debug: bool = False) -> Optional[List[_ida_idd.modinfo_t]]:
    ''' Return all loaded modules. This information is only available with a live running process.
        OBS! Modules here means loaded DLLs in the target process
        Replacement of idautils.Modules()
    '''
    if not debugger_is_running():
        log_print("You must have an active debugging session to use this function", arg_type="ERROR")
        return None

    res = []
    l_temp_mod = _ida_idd.modinfo_t()
    l_temp_result = _ida_dbg.get_first_module(l_temp_mod)
    while l_temp_result:
        if re.fullmatch(arg_name_filter_regex, l_temp_mod.name, re.IGNORECASE):
            # This note is from idautils.Modules():
            # Note: can't simply return `mod` here, since callers might
            # collect all modules in a list, and they would all re-use
            # the underlying C++ object.
            l_mod = _ida_idd.modinfo_t()
            l_mod.name = l_temp_mod.name
            l_mod.size = l_temp_mod.size
            l_mod.base = l_temp_mod.base
            l_mod.rebase_to = l_temp_mod.rebase_to
            res.append(l_mod)
            log_print(f"Module OK: {l_temp_mod}", arg_debug)
        else:
            log_print(f"Module SKIPPED: {l_temp_mod.name}, does NOT match '{arg_name_filter_regex}'", arg_debug)

        l_temp_result = _ida_dbg.get_next_module(l_temp_mod)

    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def module(arg_module_name_or_address: Union[str, EvaluateType] = None, arg_debug: bool = False) -> Optional[_ida_idd.modinfo_t]:
    ''' Find a module based on the name or an address
    OBS! Module in this context refers to a DLL loaded in the target process while it is running '''

    l_modules = modules(arg_debug=arg_debug)
    if l_modules is None:
        log_print("modules() returned None", arg_type="ERROR")
        return None

    l_addr = address(arg_module_name_or_address, arg_supress_error=True, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR and isinstance(arg_module_name_or_address, str):
        # If I could not lookup the input but it's a string, try to match against the module name
        for l_module in l_modules:
            if arg_module_name_or_address.lower() in l_module.name.lower():
                return l_module
        log_print(f"No module found for '{arg_module_name_or_address}'", arg_type="ERROR")
        return None

    for l_module in l_modules:
        if l_module.base <= l_addr <= l_module.base+l_module.size:
            return l_module

    log_print(f"No module found for '{arg_module_name_or_address}'", arg_type="ERROR")
    return None

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def load_file_into_memory(arg_file_path: str, arg_executable: bool = True, arg_debug: bool = False) -> Optional[int]:
    ''' Take a file on disk (usually shellcode) and allocates that much memory and write the file content to that memory location
    @return Returns the address the data (shellcode) was written to
    '''
    with open(arg_file_path, 'rb') as f:
        shellcode = f.read()
    res = allocate_memory_in_target(len(shellcode), arg_executable=arg_executable, arg_debug=arg_debug)
    if res is None:
        log_print("Could not allocate memory", arg_type="ERROR")
        return None
    if not write_bytes(res, shellcode, arg_debug=arg_debug):
        log_print("Writing the shellcode failed.", arg_type="ERROR")
        return None
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def win_PEB(arg_debug: bool = False) -> Optional[int]:
    ''' Gets the address to the PEB (Process Environment Block) '''
    if not debugger_is_running():
        log_print("This function can only be called in an active debugging session", arg_type="ERROR")
        return None

    l_thread_id: int = _ida_dbg.get_current_thread()
    teb_segm_name: str = f"TIB[{l_thread_id:08X}]"
    log_print(f"Segment with TEB/TIB information: '{teb_segm_name}'", arg_debug)

    teb: Optional[_ida_segment.segment_t] = _ida_segment.get_segm_by_name(teb_segm_name)
    if not teb:
        log_print(f"Could not find any segment with the name: '{teb_segm_name}'", arg_type="ERROR")
        return None
    return teb.start_ea if input_file.bits == 64 else teb.start_ea + 0x1000

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def win_GetCommandLineW(arg_debug: bool = False) -> Optional[str]:
    ''' The command line the program was started with via AppCall '''
    l_GetCommandLineW = appcall('kernel32_GetCommandLineW', "LPWSTR GetCommandLineW();", arg_debug=arg_debug)
    if not l_GetCommandLineW:
        log_print("Failed to find kernel32_GetCommandLineW", arg_type="ERROR")
        return None
    res = l_GetCommandLineW().decode('UTF-16')
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def win_GetLastError(arg_debug: bool = False) -> Optional[int]:
    ''' Calls GetLastError() via AppCall '''
    l_GetLastError = appcall('kernel32_GetLastError', "DWORD GetLastError();", arg_debug=arg_debug)
    if l_GetLastError is None:
        log_print("appcall('kernel32_GetLastError') failed", arg_type="ERROR")
        return None
    return l_GetLastError()

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def win_LoadLibraryA(arg_dll: str, arg_debug: bool = False) -> Optional[int]:
    ''' Load a DLL into the running process via AppCall '''
    l_load_library = appcall('kernel32_LoadLibraryA', "HMODULE LoadLibraryA(LPCSTR lpLibFileName);", arg_debug=arg_debug)
    if not l_load_library:
        log_print("Failed to find kernel32_LoadLibraryA", arg_type="ERROR")
        return None
    res = l_load_library(arg_dll)
    res = eval_expression(res, arg_debug=arg_debug) # res can be ida_idaapi.PyIdc_cvt_int64__ on win64 but not on win32
    if res == 0:
        l_last_error: Optional[int] = win_GetLastError()
        if l_last_error == 0xC1: # ERROR_BAD_EXE_FORMAT
            log_print("The DLL you tried to load was in a bad format and could not be loaded. Did you try to load a 32 bit DLL into a 64 bit process?", arg_type="ERROR")
        else:
            l_error_message: str = ctypes.WinError(l_last_error).strerror
            log_print(f"LoadLibraryA('{arg_dll}') failed with error code: {l_last_error} (0x{l_last_error:x}), error description: '{l_error_message}'", arg_type="ERROR") #
    return res

# TODO: maybe implement?
# @validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
# def win_GetProcAddress(arg_hmodule: EvaluateType, arg_function_name: str) -> bool:
#     ''' Calls GetProcAddress via AppCall '''
#     #     address("kernel32_GetProcAddress")
#     # FARPROC GetProcAddress(
#     #   [in] HMODULE hModule,
#     #   [in] LPCSTR  lpProcName
#     return True

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def win_FreeLibrary(arg_hmodule: EvaluateType, arg_debug: bool = False) -> bool:
    ''' Free a DLL in the running process via AppCall '''
    l_free_library = appcall('kernel32_FreeLibrary', "BOOL FreeLibraryA(HMODULE hLibModule)", arg_debug=arg_debug)
    if not l_free_library:
        log_print("Failed to find kernel32_FreeLibrary", arg_type="ERROR")
        return False

    l_module: Optional[_ida_idd.modinfo_t] = module(arg_hmodule, arg_debug=arg_debug)
    if l_module is None:
        log_print(f"address({_hex_str_if_int(arg_hmodule)}) failed", arg_type="ERROR")
        return False

    log_print(f"Freeing {l_module.name}", arg_debug)
    res = bool(l_free_library(l_module.base))
    if not res:
        l_last_error: Optional[int] = win_GetLastError()
        l_error_message: str = ctypes.WinError(l_last_error).strerror
        log_print(f"FreeLibrary('{arg_hmodule}') failed with error code: {l_last_error} (0x{l_last_error:x}), error description: '{l_error_message}'", arg_type="ERROR") #
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def win_GetProcessHeap(arg_debug: bool = False) -> Optional[int]:
    ''' Gets the default heap for this process via AppCall '''
    l_GetProcessHeap = appcall('kernel32_GetProcessHeap', "HANDLE GetProcessHeap()", arg_debug=arg_debug)
    if not l_GetProcessHeap:
        log_print("Failed to find kernel32_GetProcessHeap", arg_type="ERROR")
        return None
    res = l_GetProcessHeap()
    log_print(f"res: {res}", arg_debug)
    return eval_expression(res, arg_debug=arg_debug) # res can be ida_idaapi.PyIdc_cvt_int64__ on win64 but not on win32

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def win_GetProcessHeap_emulated(arg_debug: bool = False) -> Optional[int]:
    ''' Gets the default heap for this process by reading from the PEB

    Emulates kernelbase_GetProcessHeap()
    '''
    l_default_heap_offset = 0x30 if input_file.bits == 64 else 0x18
    l_PEB: Optional[int] = win_PEB(arg_debug=arg_debug)
    if not l_PEB:
        return None
    return pointer(l_PEB + l_default_heap_offset, arg_debug=arg_debug)


# UI ---------------------------------------------------------------------------------------------------------------------


@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def jumpto(arg_ea: EvaluateType, arg_debug: bool = False) -> bool:
    ''' Moves the current (last used) view to show the address/name/label/register.
    Replacement for ida_kernwin.jumpto()
    '''
    l_addr: int = address(arg_ea, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print(f"address({_hex_str_if_int(arg_ea)}) failed", arg_type="ERROR")
        return False
    log_print(f"Jumping to {_hex_str_if_int(l_addr)}", arg_debug)
    return _ida_kernwin.jumpto(l_addr)

j = jumpto # Make it short, make it fast!

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def ui_quick_view() -> None:
    ''' Opens the quick view where the user can pick what view they want. Default shortcut is Ctrl + 1
    This is an example on how to use the ida_kernwin.process_ui_action() function
    The input to process_ui_action() can be found in the GUI. "Options" -> "Shortcuts". The column named "Action" is the action name that goes in to the function.
    You can also list them with ida_kernwin.get_registered_actions()

    e.g.
    ida_kernwin.process_ui_action("community_base:copy_current_address")
    ida_kernwin.process_ui_action("HelpPythonAPI") --> Will open a browser window at <https://python.docs.hex-rays.com/>

    There is also execute_ui_requests. Read more <https://github.com/HexRaysSA/IDAPython/blob/9.0sp1/examples/ui/trigger_actions_programmatically.py>
    '''
    _ida_kernwin.process_ui_action('QuickView')

# New members/functions of IDA pythons objects -------------------------------------------------------------------------------------------------


@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def __repr__type_address_str(arg_self: EvaluateType) -> str:
    ''' repr with type, address and content '''
    return f"{type(arg_self)} @ 0x{address(arg_self):x} which has str():\n{str(arg_self)}"

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def __repr__type_str(arg_self: Any) -> str:
    ''' repr with type and content '''
    return f"{type(arg_self)} which has str():\n{str(arg_self)}"

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _instruction_to_bytes(arg_instruction: EvaluateType, arg_debug: bool = False) -> Optional[bytes]:
    ''' Given an instruction, return it's byte values '''
    l_addr: int = address(arg_instruction, arg_debug=arg_debug)
    if l_addr == _ida_idaapi.BADADDR:
        log_print('arg_instruction is invalid', arg_type="ERROR")
        return None
    return read_bytes(l_addr, _ida_bytes.get_item_size(l_addr) , arg_debug=arg_debug)

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _instruction_is_same_as_nop(arg_instruction: EvaluateType, arg_debug: bool = False) -> Optional[bool]:
    ''' Given an instruction, check if the operation done by the instruction is not changing any state, e.g. mov rax, rax

    OBS! This list is _NOT_ all the NOPs there are. This list will get populated as the script evolves.
    '''
    l_ins = instruction(arg_instruction, arg_debug=arg_debug)
    if l_ins is None:
        return None
    if l_ins.itype == _ida_allins.NN_nop: # e.g. nop
        return True
    if l_ins.itype == _ida_allins.NN_mov and l_ins.ops[0] == l_ins.ops[1]: # e.g. mov rax, rax
        return True
    if l_ins.itype == _ida_allins.NN_xchg and l_ins.ops[0] == l_ins.ops[1]: # e.g. xchg rax, rax
        return True

    return False

setattr(_ida_ua.insn_t, '__str__', disassemble)
setattr(_ida_ua.insn_t, '__repr__', __repr__type_address_str)
setattr(_ida_ua.insn_t, '__len__', lambda self: self.size)
setattr(_ida_ua.insn_t, 'instruction_before', property(fget=instruction_before))
setattr(_ida_ua.insn_t, 'previous_instruction', property(fget=instruction_before))
setattr(_ida_ua.insn_t, 'instruction_after', property(fget=instruction_after))
setattr(_ida_ua.insn_t, 'next_instruction', property(fget=instruction_after))
setattr(_ida_ua.insn_t, 'operands', property(fget=lambda self: [op for op in self.ops if op.type != _ida_ua.o_void])) # Replacement for ida_ua.insn_t.ops. _ida_ua.insn_t.ops is always 8 elements long even if there are not that many operands
setattr(_ida_ua.insn_t, 'function', property(fget=function))
setattr(_ida_ua.insn_t, 'mnemonic', property(fget=lambda self: _ida_ua.print_insn_mnem(address(self)).lower(), doc='Get the mnemonic. e.g. "MOV EAX, EBX" --> "mov"'))
setattr(_ida_ua.insn_t, 'bytes', property(fget=_instruction_to_bytes, doc='Get the byte values that makes up this instruction'))
setattr(_ida_ua.insn_t, 'is_jmp', property(fget=lambda self: self.itype in [_ida_allins.NN_jmp, _ida_allins.NN_jmpshort], doc='Is the instruction a JMP?'))
setattr(_ida_ua.insn_t, 'comment', property(fget=_comment_get, fset=_comment_set)) # type: ignore[arg-type]
_conditional_jmps_x64 = [_ida_allins.NN_ja, _ida_allins.NN_jae, _ida_allins.NN_jb, _ida_allins.NN_jbe, _ida_allins.NN_jc, _ida_allins.NN_jcxz, _ida_allins.NN_je, _ida_allins.NN_jecxz, _ida_allins.NN_jg, _ida_allins.NN_jge, _ida_allins.NN_jl, _ida_allins.NN_jle, _ida_allins.NN_jna, _ida_allins.NN_jnae, _ida_allins.NN_jnb, _ida_allins.NN_jnbe, _ida_allins.NN_jnc, _ida_allins.NN_jne, _ida_allins.NN_jng, _ida_allins.NN_jnge, _ida_allins.NN_jnl, _ida_allins.NN_jnle, _ida_allins.NN_jno, _ida_allins.NN_jnp, _ida_allins.NN_jns, _ida_allins.NN_jnz, _ida_allins.NN_jo, _ida_allins.NN_jp, _ida_allins.NN_jpe, _ida_allins.NN_jpo, _ida_allins.NN_jrcxz, _ida_allins.NN_js, _ida_allins.NN_jz]
_conditional_jmps_MIPS = [_ida_allins.MIPS_beqz] # TODO: This one is NOT complete
_conditional_jmps = _conditional_jmps_x64 # TODO: When a new file is opened, point this to the correct list
setattr(_ida_ua.insn_t, 'is_jcc', property(fget=lambda self: self.itype in _conditional_jmps, doc='Is the instruction a conditional JMP?'))
setattr(_ida_ua.insn_t, 'is_call', property(fget=_ida_idp.is_call_insn, doc='Is the instruction a call?'))
setattr(_ida_ua.insn_t, 'is_ret', property(fget=_ida_idp.is_ret_insn, doc='Is the instruction a return?'))
setattr(_ida_ua.insn_t, 'is_same_as_nop', property(fget=_instruction_is_same_as_nop, doc='Is the instruction a NOP? (or code that does nothing e.g. mov rax, rax)'))
setattr(_ida_funcs.func_t, '__str__', lambda self: f"name: {_ida_funcs.get_func_name(self.start_ea)},  start_ea: 0x{self.start_ea:x}, end_ea: 0x{self.end_ea:x}")
setattr(_ida_funcs.func_t, '__repr__', __repr__type_address_str)
setattr(_ida_funcs.func_t, '__len__', lambda self: self.end_ea - self.start_ea)
setattr(_ida_funcs.func_t, 'decompiled', property(fget=decompile, doc="Returns a ida_hexrays.cfuncptr_t, same as the decompile() function returns"))
setattr(_ida_funcs.func_t, 'prototype', property(fget=function_prototype, fset=set_type)) # type: ignore[arg-type]
setattr(_ida_funcs.func_t, 'name', property(fget=name, fset=name, doc="Get or set the name of the function")) # type: ignore[arg-type]
setattr(_ida_funcs.func_t, 'address', property(fget=address))
setattr(_ida_funcs.func_t, 'return_type', property(fget=lambda self: decompile(self).type.get_rettype())) # type: ignore[union-attr]
setattr(_ida_funcs.func_t, 'is_library_function', property(fget=is_library_function))
setattr(_ida_funcs.func_t, 'is_lumina_name', property(fget=_is_lumina_name))

__GLOBAL_KEEP_REFERENCE_TO_AVOID_MEMORY_CORRUPTION__ = 0
@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _function_arguments(arg_ea: EvaluateType, arg_debug: bool = False) -> Optional[_ida_typeinf.func_type_data_t]:
    ''' Internal function. Gets the arguments to a function '''

    global __GLOBAL_KEEP_REFERENCE_TO_AVOID_MEMORY_CORRUPTION__
    l_function = function(arg_ea, arg_debug=arg_debug)
    if l_function is None:
        log_print(f"function({_hex_str_if_int(arg_ea)}) failed", arg_type="ERROR")
        return None
    l_tif = _ida_typeinf.tinfo_t()
    if not _ida_nalt.get_tinfo(l_tif, l_function.address):
        log_print(f"ida_nalt.get_tinfo(_tif, 0x{l_function.address:x}) failed", arg_type="ERROR")
        return None
    l_funcdata = _ida_typeinf.func_type_data_t()
    if not l_tif.get_func_details(l_funcdata):
        log_print("tif.get_func_details() failed", arg_type="ERROR")
        return None

    # TODO: You get memory corruption if you do: community_base.function(<address>).arguments[0], IDA bug
    __GLOBAL_KEEP_REFERENCE_TO_AVOID_MEMORY_CORRUPTION__ = l_funcdata
    return l_funcdata

setattr(_ida_funcs.func_t, 'arguments', property(fget=_function_arguments))
setattr(_ida_funcs.func_t, 'calls', property(fget=_assembler_calls))
setattr(_ida_funcs.func_t, '__call__', lambda *args: appcall(args[0])(*args[1:])) # type: ignore[misc] # py_lstrcmpA = cb.function("lstrcmpA"); py_lstrcmpA("input_text", "input_text") # TODO: This is dangerous, maybe remove?
setattr(_ida_funcs.func_t.__call__, '__doc__', f"Calls the function via AppCall. Read more: {links()['links']['appcall_guide']}")
@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _argloc_t_type_to_str(arg_argloc: _ida_typeinf.argloc_t) -> Optional[str]:
    ''' Internal function. Convert the int from argloc.atype() to a human readable string '''
    if isinstance(arg_argloc, _ida_typeinf.funcarg_t):
        arg_argloc = arg_argloc.argloc

    l_argloc_dict: Dict[int, str] = {_ida_typeinf.__dict__[argloc_str]: argloc_str for argloc_str in dir(_ida_typeinf) if argloc_str.startswith('ALOC_')} # _argloc_dict[_ida_typeinf.ALOC_STACK: int] -> "ALOC_STACK": str
    res = l_argloc_dict.get(arg_argloc.atype(), None)
    if not res:
        log_print(f"Could not find any ALOC_* type for arg_argloc.atype(): {arg_argloc.atype()}", arg_type="ERROR")
        log_print(f"Since atype() is so large, it hints about memory corruption.\nThe possible values are:\n{l_argloc_dict}", arg_argloc.atype() > 1000)
        return None

    return res
setattr(_ida_typeinf.argloc_t, '__str__', _argloc_t_type_to_str)
setattr(_ida_typeinf.argloc_t, '__repr__', __repr__type_str)
setattr(_ida_typeinf.argloc_t, 'atype_as_str', property(fget=_argloc_t_type_to_str))
@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _funcarg_t_str(arg_funcarg_t: _ida_typeinf.funcarg_t) -> str:
    ''' Internal function. Makes a nice string from a ida_typeinf.funcarg_t object '''

    res = f"argument: '{str(arg_funcarg_t.type)} {arg_funcarg_t.name if arg_funcarg_t.name else '<no name>' }' with argument location: {str(arg_funcarg_t.argloc)}"
    if arg_funcarg_t.argloc.is_reg1():
        res += f'\nRegister: {str(arg_funcarg_t.register.name)}: {(f"0x{_register(arg_funcarg_t.register):x}" if debugger_is_running() else "<only when debugger is running>")}'
    # TODO: elif on stack: print stack var
    return res
setattr(_ida_typeinf.funcarg_t, '__str__', _funcarg_t_str)
setattr(_ida_typeinf.funcarg_t, '__repr__', __repr__type_str)
setattr(_ida_typeinf.funcarg_t, 'size', property(fget=lambda self: len(self.type)))
setattr(_ida_typeinf.funcarg_t, 'register', property(fget=lambda self: registers._as_dict[_ida_idp.get_reg_name(self.argloc.reg1(), self.size)] if self.argloc.is_reg1() else None))
setattr(_ida_typeinf.func_type_data_t, '__str__', lambda self: '[ ' + "\n\n".join([repr(funcarg_t) for funcarg_t in self]) + '\n]')
setattr(_ida_typeinf.func_type_data_t, '__repr__', __repr__type_str)
setattr(_ida_typeinf.tinfo_t, '__repr__', __repr__type_str)
setattr(_ida_typeinf.tinfo_t, '__len__', lambda self: self.get_size() if self.get_size() != _ida_typeinf.BADSIZE else 0)
setattr(_ida_typeinf.tinfo_t, '__bool__', lambda self: self.is_well_defined())
setattr(_ida_typeinf.tinfo_t, 'size', property(fget=len))
setattr(_ida_typeinf.tinfo_t, 'return_type', property(fget=lambda self: self.get_rettype() if self.is_func() else None))
setattr(_ida_kernwin.simpleline_t, '__str__', lambda self: _ida_lines.tag_remove(self.line))
setattr(_ida_kernwin.simpleline_t, '__repr__', __repr__type_str)
setattr(_ida_pro.strvec_t, '__str__', lambda self: "\n".join([str(simpleline) for simpleline in self]))
setattr(_ida_segment.segment_t, '__repr__', __repr__type_str)
setattr(_ida_segment.segment_t, '__str__', lambda self: f".name_as_str: {self.name_as_str}, .class_as_str: {self.class_as_str}, .start_ea: 0x{self.start_ea:x}, .end_ea: 0x{self.end_ea:x}, .readable: {self.readable}, .writable: {self.writable}, .executable: {self.executable}")
setattr(_ida_segment.segment_t, '__len__', lambda self: self.size())
setattr(_ida_segment.segment_t, 'readable', property(fget=lambda self: bool(self.perm & _ida_segment.SEGPERM_READ), fset=lambda self, value: _segment_permissions(self, arg_readable=value))) # type: ignore[arg-type]
setattr(_ida_segment.segment_t, 'writable', property(fget=lambda self: bool(self.perm & _ida_segment.SEGPERM_WRITE), fset=lambda self, value: _segment_permissions(self, arg_writable=value))) # type: ignore[arg-type]
setattr(_ida_segment.segment_t, 'executable', property(fget=lambda self: bool(self.perm & _ida_segment.SEGPERM_EXEC), fset=lambda self, value: _segment_permissions(self, arg_executable=value))) # type: ignore[arg-type]
setattr(_ida_segment.segment_t, 'name_as_str', property(fget=_ida_segment.get_segm_name, fset=_ida_segment.set_segm_name)) # '.name' is already taken but it contains an int?
setattr(_ida_segment.segment_t, 'class_as_str', property(fget=_ida_segment.get_segm_class, fset=_ida_segment.set_segm_class))
setattr(_ida_segment.segment_t, 'bits', property(fget=lambda self: 0x10 << self.bitness))
_data_type_sizes: Dict[int, int] = {_ida_ua.dt_byte: 1, _ida_ua.dt_word: 2, _ida_ua.dt_dword: 4, _ida_ua.dt_qword: 8, _ida_ua.dt_float: 4, _ida_ua.dt_double: 8, _ida_ua.dt_byte16: 16, _ida_ua.dt_byte32: 32, _ida_ua.dt_byte64: 64, _ida_ua.dt_half: 2}
@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _op_t_is_reg(self: _ida_ua.op_t, arg_register_name_or_index: Union[int, str, _ida_idp.reg_info_t]) -> bool:
    ''' Replacement for ida_ua.op_t.is_reg() to allow to also check for register name or _ida_idp.reg_info_t '''
    if isinstance(arg_register_name_or_index, int):
        return self.reg == arg_register_name_or_index
    if isinstance(arg_register_name_or_index, str):
        l_reg_info = _ida_idp.reg_info_t()
        return _ida_idp.parse_reg_name(l_reg_info, arg_register_name_or_index) and l_reg_info.reg == self.reg and _data_type_sizes[self.dtype] == l_reg_info.size
    # isinstance(arg_register_name_or_index, _ida_idp.reg_info_t):
    return arg_register_name_or_index.reg == self.reg and _data_type_sizes[self.dtype] == arg_register_name_or_index.size


setattr(_ida_ua.op_t, 'is_reg', _op_t_is_reg)
_operand_type = _int_to_str_dict_from_module(_ida_ua, "o_.*")
@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _op_t__str__(self: _ida_ua.op_t, arg_debug: bool = False) -> str:
    ''' Internal function. More verbose output in the __str__() of ida_ua.op_t '''
    if self.type == _ida_ua.o_void:
        return "<<< invalid operand >>> IDA use an ida_ua.op_t with .type == ida_ua.o_void to signal that it's invalid. I don't like this."

    l_parsed = _operand_parser(self, arg_debug=arg_debug)
    if l_parsed is None:
        log_print(f"Unknown operand type, we got 0x{self.type:x} which I cannot handle.", arg_type="ERROR")
        return "<<< Can _NOT_ parse this operand >>>"

    log_print(f"l_parsed: {l_parsed}", arg_debug)

    l_temp = l_parsed.get('register', None)
    if l_temp:
        return str(l_temp)

    l_temp = l_parsed.get('address', None)
    if l_temp:
        return _hex_str_if_int(l_temp, arg_debug=arg_debug)

    l_temp = l_parsed.get('value', None)
    if l_temp:
        return _hex_str_if_int(l_temp, arg_debug=arg_debug)

    l_base_reg = l_parsed.get('base_register', None)
    if l_base_reg:
        l_displacement = l_parsed['displacement']
        l_displacement_string = _signed_hex_text(l_displacement) if l_displacement else ""
        l_scale_string = ""
        if l_parsed.get('index_register', None):
            l_scale = l_parsed['scale']
            l_scale_const = f"*{l_parsed['scale']}" if l_parsed['scale'] > 1 else ""
            l_index_reg = l_parsed['index_register']
            l_scale_string = f"+{l_index_reg.name}{l_scale_const}" if l_scale else ""
        return f"[{l_base_reg.name}{l_scale_string}{l_displacement_string}]"

    log_print("Could not parse the given ida_ua.op_t.", arg_type='ERROR')
    return "<<< invalid operand, could _NOT_ parse it >>>"
setattr(_ida_ua.op_t, '__str__', _op_t__str__)
setattr(_ida_ua.op_t, '__repr__', lambda self: f"{type(self)} with operand_type {_operand_type.get(self.type, '<unknown _ida_ua.o_???>')} which has str():\n{str(self)}")
@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _op_t_to_register(arg_operand: _ida_ua.op_t, arg_debug: bool = False) -> Optional[_ida_idp.reg_info_t]:
    ''' Send in an operand and if the operand is a register, then return the register as ida_idp.reg_info_t '''
    res = None
    if arg_operand.type in [_ida_ua.o_reg, _ida_ua.o_displ, _ida_ua.o_phrase]:
        l_reg_name = _ida_idp.get_reg_name(arg_operand.reg, _data_type_sizes[arg_operand.dtype])
        res = _ida_idp.reg_info_t()
        _ida_idp.parse_reg_name(res, l_reg_name)
    else:
        log_print(f"arg_operand is {str(arg_operand)} which is something I cannot handle right now", arg_type="ERROR")
        return None
    log_print(f"res: {repr(res)}", arg_debug)
    return res
setattr(_ida_ua.op_t, 'register', property(fget=_op_t_to_register))
setattr(_ida_ua.op_t, 'name', property(fget=name))
setattr(_ida_ua.op_t, 'as_dict', property(fget=_operand_parser))
setattr(_ida_ua.op_t, '__eq__', lambda self, other: self.type == other.type and self.dtype == other.dtype and self.value == other.value and self.value64 == other.value64 and self.specflag1 == other.specflag1 and self.specflag2 == other.specflag2 and self.reg == other.reg and self.addr == other.addr)
setattr(_ida_idp.reg_info_t, '__str__', lambda self: f".name: {_ida_idp.get_reg_name(self.reg, self.size)}, .size: 0x{self.size:x}, .register_index: {self.reg}, .value: " + (_hex_str_if_int(_register(self)) if debugger_is_running() else "<only when debugger is running>") + "\n")
setattr(_ida_idp.reg_info_t, '__repr__', __repr__type_str)
setattr(_ida_idp.reg_info_t, '__len__', lambda self: self.size)
setattr(_ida_idp.reg_info_t, 'name', property(fget=lambda self: _ida_idp.get_reg_name(self.reg, self.size)))
setattr(_ida_idp.reg_info_t, 'register_index', _ida_idp.reg_info_t.reg)
setattr(_ida_idp.reg_info_t, 'value', property(fget=_register, fset=_register)) # type: ignore[arg-type]
setattr(_ida_idp.reg_info_t, '__add__', lambda self, other: eval_expression(self) + eval_expression(other)) # type: ignore[operator]
setattr(_ida_idp.reg_info_t, '__radd__', _ida_idp.reg_info_t.__add__)
setattr(_ida_idp.reg_info_t, '__iadd__', lambda self, other: self if _register(arg_register=self, arg_set_value=eval_expression(self) + eval_expression(other)) else self) # type: ignore[operator]
setattr(_ida_idp.reg_info_t, '__sub__', lambda self, other: eval_expression(self) - eval_expression(other)) # type: ignore[operator]
setattr(_ida_idp.reg_info_t, '__rsub__', lambda other, self: _ida_idp.reg_info_t.__sub__(self, other))
setattr(_ida_idp.reg_info_t, '__isub__', lambda self, other: self if _register(arg_register=self, arg_set_value=eval_expression(self) - eval_expression(other)) else self) # type: ignore[operator]
setattr(_ida_idp.reg_info_t, '__eq__', lambda self, other: self is other or self.name == other)
setattr(_ida_hexrays.carg_t, '__repr__', lambda self: f"{type(self)} which looks like:\n{self.type} {str(self)}")
setattr(_ida_hexrays.carg_t, 'name', property(fget=str)) # TODO: Bad idea?
setattr(_ida_hexrays.carglist_t, '__repr__', lambda self: f"{type(self)} which looks like:\n{' '.join([chr(0x0D)+repr(arg)+chr(0x0D) for arg in self])}")
setattr(_ida_hexrays.cfuncptr_t, '__str__', lambda self: pseudocode(self, arg_force_fresh_decompilation=True))
setattr(_ida_hexrays.cfuncptr_t, '__repr__', lambda self: __repr__type_address_str(self)[0:200])
setattr(_ida_hexrays.cfuncptr_t, 'address', property(fget=address))
setattr(_ida_hexrays.cfuncptr_t, 'prototype', property(fget=function_prototype))
setattr(_ida_hexrays.cfuncptr_t, 'return_type', property(fget=lambda self: self.type.get_rettype(), doc='The tinfo_t of the return value'))
setattr(_ida_hexrays.cfuncptr_t, 'name', property(fget=name, fset=lambda self, new_name: name(self, arg_set_name=new_name, arg_force=True))) # type: ignore[union-attr, arg-type]
setattr(_ida_hexrays.cfuncptr_t, 'local_variables', property(fget=lambda self: {var.name: var for var in self.lvars}))
setattr(_ida_hexrays.cfuncptr_t, 'calls', property(fget=_decompiler_calls))
setattr(_ida_hexrays.cfuncptr_t, 'is_lumina_name', property(fget=_is_lumina_name))
setattr(_ida_hexrays.citem_t, '__str__', lambda self: f"{_ida_lines.tag_remove(self.print1(None))}")
setattr(_ida_hexrays.citem_t, '__repr__', __repr__type_address_str)
setattr(_ida_hexrays.cexpr_t, '__repr__', lambda self: f"{type(self)} with opname: '{self.opname}' and to_specific_type.opname: '{self.to_specific_type.opname}' @ 0x{address(self):x} which looks like:\n{str(self)}"  ) # TODO: address of cexpr_t is not OK according to the type hints
setattr(_ida_hexrays.cexpr_t, 'arguments', property(fget=lambda self: self._get_a() if self.opname == 'call' else None)) # Used for cot_call
setattr(_ida_hexrays.cexpr_t, 'first_operand', _ida_hexrays.cexpr_t.x) # Better name
setattr(_ida_hexrays.cexpr_t, 'second_operand', _ida_hexrays.cexpr_t.y) # Better name
setattr(_ida_hexrays.cexpr_t, 'third_operand', _ida_hexrays.cexpr_t.z) # Better name
setattr(_ida_hexrays.cexpr_t, 'variable', _ida_hexrays.cexpr_t.v) # Better name. used for cot_var
setattr(_ida_hexrays.cexpr_t.v, '__doc__', 'Short name for variable. Only used for cot_var')
setattr(_ida_hexrays.cexpr_t, 'value', property(fget=lambda self: self.numval() if self.opname == 'num' else None)) # Used for cot_num
setattr(_ida_hexrays.cexpr_t, 'float', _ida_hexrays.cexpr_t.fpc) # Used for cot_fnum
setattr(_ida_hexrays.cexpr_t, 'target_ea', property(fget=lambda self: self.x.obj_ea if self.opname == 'call' else None)) # Used for cot_obj. Use this to get the address that the call is calling to
setattr(_ida_hexrays.cexpr_t, 'member_offset', _ida_hexrays.cexpr_t.m) # Used for cot_memptr and cot_memref
setattr(_ida_hexrays.cinsn_t, '__repr__', lambda self: f"{type(self)} with opname: '{self.opname}' and to_specific_type.opname: '{self.to_specific_type.opname}' @ 0x{address(self):x} which looks like:\n{str(self)}"  ) # "cinsn_t represents statements supported by Hex-Rays (cit_for, cit_if, cit_return etc...)" source: https://hex-rays.com/blog/hex-rays-decompiler-primer
setattr(_ida_hexrays.casm_t, '__repr__', lambda self: "__asm { \n" + "\n".join(["\t" + disassemble(x, arg_show_size=False, arg_show_bytes=False) for x in self]) + "\n}") # type: ignore[operator]
setattr(_ida_hexrays.lvar_t, '__str__', lambda self: f"{str(self.type()).replace(' *','*')} {str(self.name)}")
setattr(_ida_hexrays.lvar_t, '__repr__', lambda self: f"{type(self)} which looks like:\n{str(self)}")
setattr(_ida_hexrays.lvar_t, '__len__', lambda self: self.type().size)
setattr(_ida_hexrays.lvar_t, 'register', property(fget=lambda self: registers._as_dict[_ida_idp.get_reg_name(_ida_hexrays.mreg2reg(self.get_reg1(), len(self)), len(self))] if self.is_reg1() else None))
setattr(_ida_hexrays.lvars_t, "__repr__", lambda self: "[" +  "\n".join([repr(var) for var in self]) + "]")
setattr(_ida_hexrays.var_ref_t, '__str__', lambda self: str(self.getv())) # self.getv() returns a _ida_hexrays.lvar_t
setattr(_ida_hexrays.var_ref_t, '__repr__', __repr__type_str)
setattr(_ida_hexrays.ctree_items_t, '__repr__', lambda self: f"{type(self)} which looks like:\n[{', '.join([str(citem) for citem in self])}]")
setattr(_ida_idd.Appcall_callable__, '__str__', lambda self: str(function(self)))
setattr(_ida_idd.Appcall_callable__, '__repr__', __repr__type_address_str)
setattr(_ida_typeinf.enum_member_t, '__str__', lambda self: f"{self.name} = 0x{self.value:x}, // {self.value}")
setattr(_ida_typeinf.enum_member_t, '__repr__', __repr__type_str)
setattr(_ida_typeinf.enum_type_data_t, '__repr__', lambda self: "\n".join([str(member) for member in self]))
setattr(_ida_dbg.bpt_t, '__str__', lambda self: f"ea: 0x{self.ea:x}, is hardware breakpoint (is_hwbpt): {self.is_hwbpt()}, enabled: {self.enabled()}, eval_lang: {self.elang}, condition: {self.condition}")
setattr(_ida_dbg.bpt_t, '__repr__', __repr__type_address_str)
setattr(_ida_dbg.bpt_t.elang, "__doc__", "The langauge used to evaluate what to do when we hit this breakpoint. Allowed values are IDC or Python")
setattr(_ida_idd.modinfo_t, '__str__', lambda self: f"name: {self.name}, base: 0x{self.base:x}, size: 0x{self.size:x}, rebase_to: 0x{self.rebase_to:x}")
setattr(_ida_idd.modinfo_t, '__repr__', __repr__type_address_str)
setattr(_ida_range.range_t, '__str__', lambda self: f"start_ea: {_hex_str_if_int(self.start_ea)} --> end_ea: {_hex_str_if_int(self.end_ea)}")
setattr(_ida_range.range_t, '__repr__', __repr__type_address_str)


# TESTS ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _test_appcall_on_Windows(arg_debug: bool = False) -> bool:
    res = True
    l_GetProcessHeap_res = win_GetProcessHeap(arg_debug=arg_debug)
    if l_GetProcessHeap_res is None:
        log_print('win_GetProcessHeap returned None', arg_type="ERROR")
        return False
    res &= (l_GetProcessHeap_res == win_GetProcessHeap_emulated(arg_debug=arg_debug)) # win_GetProcessHeap --> appcall,

    if res:
        log_print('Appcall tests OK!', arg_type="INFO")
    else:
        log_print('Appcall tests failed!', arg_type="ERROR")
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _test_mem_alloc_write_read(arg_debug: bool = False) -> bool:
    ''' Tests: allocate_memory_in_target(), write_string(), write_bytes(), read_bytes(), string()
        Needs a running process.
    '''
    res = True
    l_memory = allocate_memory_in_target(0x1000, arg_debug=arg_debug)
    if l_memory is None:
        log_print('Failed to allocate memory', arg_type="ERROR")
        return False
    log_print(f"Allocated 0x1000 bytes at 0x{l_memory:x}", arg_type="INFO")
    l_input_test_string: str = "This string is for the tests!"
    write_string(l_memory, l_input_test_string, arg_debug=arg_debug) # write_string --> write_bytes --> read_bytes
    l_test_string = string(l_memory, arg_debug=arg_debug)
    res &= ((l_input_test_string) == l_test_string)
    log_print(f"cstring test: {res}", arg_debug)
    log_print(f"<<< FAILED >>> cstring test: {res}", arg_actually_print=not res, arg_type="ERROR")

    l_input_test_string_wide: bytes = b"T\x00e\x00s\x00t\x00\x00\x00"
    write_bytes(l_memory, l_input_test_string_wide, arg_debug=arg_debug)
    l_wide_string_res = string(l_memory, arg_encoding="UCS-2", arg_debug=arg_debug)
    res &= ("Test" == l_wide_string_res)
    log_print(f"simple wide string test: {res}", arg_debug)
    log_print(f"<<< FAILED >>> cstring test: {res}", arg_actually_print=not res, arg_type="ERROR")

    l_non_english_char_test_string: str = "åäö"
    l_encoding = "UTF-8"
    write_bytes(l_memory, "00" * 32, arg_debug=arg_debug)
    write_bytes(l_memory, l_non_english_char_test_string.encode(l_encoding), arg_debug=arg_debug)
    l_nonenglish_res = string(l_memory, arg_encoding=l_encoding, arg_debug=arg_debug)
    if l_nonenglish_res is None:
        log_print("string() failed", arg_type="ERROR")
        return False
    res &= (l_nonenglish_res == l_non_english_char_test_string)
    log_print(f"l_non_english_char_test_string: {' '.join(hex_parse(l_non_english_char_test_string.encode(l_encoding)))}", arg_debug)
    log_print(f"l_nonenglish_res: {' '.join(hex_parse(l_nonenglish_res.encode(l_encoding)))}", arg_debug)
    log_print(f"non english string test: {res}", arg_debug)
    log_print(f"<<< FAILED >>> {l_encoding} test: {res}", arg_actually_print=not res, arg_type="ERROR")

    l_encoding = "UTF-16LE"
    write_bytes(l_memory, "00" * 32, arg_debug=arg_debug)
    write_bytes(l_memory, l_non_english_char_test_string.encode(l_encoding), arg_debug=arg_debug)
    l_nonenglish_res = string(l_memory, arg_encoding=l_encoding, arg_debug=arg_debug)
    if l_nonenglish_res is None:
        log_print("string() failed", arg_type="ERROR")
        return False
    res &= (l_nonenglish_res == l_non_english_char_test_string)
    log_print(f"l_non_english_char_test_string: {' '.join(hex_parse(l_non_english_char_test_string.encode(l_encoding)))}", arg_debug)
    log_print(f"l_nonenglish_res: {' '.join(hex_parse(l_nonenglish_res.encode(l_encoding)))}", arg_debug)
    log_print(f"non english string test: {res}", arg_debug)
    log_print(f"<<< FAILED >>> {l_encoding} test: {res}", arg_actually_print=not res, arg_type="ERROR")

    l_encoding = "Latin-1"
    write_bytes(l_memory, "00" * 32, arg_debug=arg_debug)
    write_bytes(l_memory, l_non_english_char_test_string.encode(l_encoding), arg_debug=arg_debug)
    l_nonenglish_res = string(l_memory, arg_encoding=l_encoding, arg_debug=arg_debug)
    if l_nonenglish_res is None:
        log_print("string() failed", arg_type="ERROR")
        return False
    res &= (l_nonenglish_res == l_non_english_char_test_string)
    log_print(f"l_non_english_char_test_string: {' '.join(hex_parse(l_non_english_char_test_string.encode(l_encoding)))}", arg_debug)
    log_print(f"l_nonenglish_res: {' '.join(hex_parse(l_nonenglish_res.encode(l_encoding)))}", arg_debug)
    log_print(f"non english string test: {res}", arg_debug)
    log_print(f"<<< FAILED >>> {l_encoding} test: {res}", arg_actually_print=not res, arg_type="ERROR")

    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _test_modules_on_Windows(arg_debug: bool = False) -> bool:
    ''' Tests: modules(), read_bytes()
        Needs a running process.
    '''
    l_modules = modules(arg_debug=arg_debug)
    if l_modules is None:
        log_print('modules() returned None', arg_type="ERROR")
        return False
    l_MZ_header = read_bytes(l_modules[0].base, 0x2)
    if l_MZ_header is None:
        log_print('read_bytes() returned None', arg_type="ERROR")
        return False
    res = True
    res &= (l_MZ_header == b'MZ')
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _test_eval_expression(arg_debug: bool = False) -> bool:
    ''' Tests: eval_expression() '''
    res = True
    res &= (eval_expression("11") == 0x0B)
    log_print(f'Test 1: {res}', arg_debug)
    res &= (eval_expression("11+0") == 11)
    log_print(f'Test 2: {res}', arg_debug)
    res &= (_idaapi_str2ea("This is an invalid address!") == _ida_idaapi.BADADDR)
    log_print(f'Test 3: {res}', arg_debug)
    res &= (_ida_kernwin.str2ea("11") == 0x11)
    log_print(f'Test 4: {res}', arg_debug)
    res &= (_ida_kernwin.str2ea("11+0") == 0x0B)
    log_print(f'Test 5: {res}', arg_debug)
    res &= (eval_expression("This is an invalid address") is None)
    log_print(f'Test 6: {res}', arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _test_all(arg_debug: bool = False) -> bool:
    ''' Tests all tests we have. This is NOT complete and needs to be extended '''
    l_test_functions = {'_test_appcall_on_Windows': _test_appcall_on_Windows(arg_debug=arg_debug),
                        '_test_mem_alloc_write_read': _test_mem_alloc_write_read(arg_debug=arg_debug),
                        '_test_modules_on_Windows': _test_modules_on_Windows(arg_debug=arg_debug),
                        '_test_address': _test_eval_expression(arg_debug=arg_debug)
                        }
    log_print(str(l_test_functions), arg_type="INFO")
    return all(l_test_functions.values())


# EXPERIMENTAL ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _basic_string_print(arg_ea: EvaluateType, arg_str_len_threshold: int = 400, arg_debug: bool = False) -> Optional[str]:
    ''' Try to parse a basic string and print it. OBS! Since basic_string is depending on the compiler, this function may need som slight modifications for your project. Tags: std_string, std::string, std_wstring, std::wstring '''
    log_print(f"You gave arg_ea: {arg_ea}", arg_debug)
    l_p_string = pointer(arg_ea)
    if l_p_string is None:
        log_print("pointer() failed", arg_type="ERROR")
        return None
    log_print(f"str is at 0x{l_p_string:x}", arg_debug)
    l_str_len: int = _ida_bytes.get_qword(address(arg_ea) + pointer_size())
    log_print(f"with len: 0x{l_str_len:x}", arg_debug)
    if l_str_len > arg_str_len_threshold:
        log_print(f"String len is VERY high (0x{l_str_len:x}), this is probably wrong, aborting", arg_type="WARNING")
        return None

    res = c_string(l_p_string, arg_len=l_str_len) if l_str_len else ""
    log_print(f"Read string is: {res}", arg_debug)
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _export_names_and_types(arg_save_to_file: str = "",
                                         arg_allow_library_functions: bool = True,
                                         arg_list_of_functions: Union[List[_ida_funcs.func_t], List[int], None] = None,
                                         arg_full_export: bool = False,
                                         arg_debug: bool = False) -> Dict[str, Dict[str,str]]:
    ''' Exports functions name and function type so we can import that file in another project that use the same name and function prototype
    # TODO: WARNING! This function is "working" but is very slow and I am not happy with how it works right now, consider it experimental
    '''
    res = {}
    if not arg_save_to_file:
        arg_save_to_file = input_file.idb_path + ".export_names_and_functions.json"
    log_print(f"Saving exported data to {arg_save_to_file}", arg_debug)

    if not arg_list_of_functions:
        arg_list_of_functions = functions(arg_allow_library_functions=arg_allow_library_functions, arg_debug=arg_debug)

    l_counter = 0
    for func_start_address in arg_list_of_functions:
        func: Optional[_ida_funcs.func_t] = function(func_start_address)
        if func is None:
            log_print("function(func) failed", arg_type="ERROR")
            continue
        l_counter += 1
        l_data_to_export: Dict[str, str] = {}
        l_data_to_export["name"] = name(func, arg_demangle_name=False) or f"sub_{func.start_ea:X}"
        if arg_full_export: # OBS! This is VERY SLOW
            l_data_to_export["demangled_name"] = name(func, arg_demangle_name=True) or f"sub_{func.start_ea:X}"
            l_data_to_export["prototype"] = function_prototype(func.start_ea, arg_allow_comments=False, arg_debug=arg_debug)
            _t = _ida_typeinf.tinfo_t()
            _ida_hexrays.get_type(func.start_ea, _t, 0)
            l_data_to_export["type"] = str(_t)
            l_data_to_export["comment"] = comment(func.start_ea) or ""
            l_data_to_export["rva"] = f"0x{rva(func.start_ea):x}"

        res[f"0x{func.start_ea:x}"] = l_data_to_export

        if l_counter % 100 == 0: # TODO: During debugging, its nice to see the progress and get an idea on how long time it will take
            log_print(f"l_counter = {l_counter}")
            with open(arg_save_to_file + f".{l_counter}.json", "w", encoding="utf-8", newline="\n") as f:
                json.dump(res, f, ensure_ascii=False, indent=4, default=str)

    with open(arg_save_to_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=4, default=str)
    log_print(f"Wrote JSON to:\n'{arg_save_to_file}'", arg_type="INFO")
    return res

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def _ignore_cast(arg_expr: _ida_hexrays.cexpr_t) -> _ida_hexrays.cexpr_t:
    ''' Helper function for (<type>)variable_name in the decompiler '''
    if arg_expr.opname == 'cast':
        return arg_expr.first_operand
    return arg_expr

@validate_call(config={"arbitrary_types_allowed": True, "strict": True, "validate_return": True})
def errors_find_type_errors(arg_ea: EvaluateType, arg_force_fresh_decompilation: bool = True, arg_debug: bool = False) -> Optional[bool]:
    '''  Find type errors such as <int> - <ptr> and in the future: <ptr> + <ptr> '''

    l_cfunc = decompile(arg_ea, arg_force_fresh_decompilation=arg_force_fresh_decompilation, arg_debug=arg_debug)
    if not l_cfunc:
        return None

    for _t in l_cfunc.treeitems:
        _t = _ida_hexrays.citem_to_specific_type(_t)

        if _t.opname == 'sub': # checking for <int> - <ptr>
            left = _ignore_cast(_t.first_operand)
            right = _ignore_cast(_t.second_operand)

            if left.opname == 'var':
                left_type = left.variable.getv().type()
                if left_type.is_int():
                    if right.opname == 'var':
                        right_type = right.variable.getv().type()
                        if right_type.is_ptr():
                            log_print(f'Found invalid types at "{_t}" where {left} is int and {right} is ptr', arg_type="WARNING")
                            return True
        elif _t.opname == 'eq': # Checking for a <ptr> == <integer value> which is very rare
            left = _ignore_cast(_t.first_operand)
            right = _ignore_cast(_t.second_operand)
            if left.opname == 'var':
                left_type = left.variable.getv().type()
                if left_type.is_ptr():
                    if right.opname == 'num':
                        log_print(f'WARNING! Found possible invalid types at "{_t}" where {left} is ptr and {right} is num')
                        return True
    return False
