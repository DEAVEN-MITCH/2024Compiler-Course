from . import c_parser
from . import cpp_parser
from . import csharp_parser
from . import go_parser
from . import java_parser
from . import javascript_parser
from . import kotlin_parser
from . import llvm_parser
from . import php_parser
from . import python_parser
from . import ruby_parser
from . import rust_parser
from . import smali_parser
from . import typescript_parser

PARSERS = {
    "c"         : c_parser.Parser,
    "cpp"       : cpp_parser.Parser,
    "csharp"    : csharp_parser.Parser,
    "rust"      : rust_parser.Parser,
    "go"        : go_parser.Parser,
    "java"      : java_parser.Parser,
    "javascript": javascript_parser.Parser,
    "typescript": typescript_parser.Parser,
    "kotlin"    : kotlin_parser.Parser,
    "llvm"      : llvm_parser.Parser,
    "python"    : python_parser.Parser,
    "ruby"      : ruby_parser.Parser,
    "smali"     : smali_parser.Parser,
    "php"       : php_parser.Parser,
}
