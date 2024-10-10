from PyQt5 import QtGui, QtCore

class PythonHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        keyword_format = QtGui.QTextCharFormat()
        keyword_format.setForeground(QtGui.QColor("#569cd6"))
        keyword_format.setFontWeight(QtGui.QFont.Bold)
        keywords = ["def", "class", "for", "if", "elif", "else", "while", "return", "import", "from", "as", "try",
                    "except", "finally", "with"]
        self.add_highlighting_rule(keywords, keyword_format)

        function_format = QtGui.QTextCharFormat()
        function_format.setFontItalic(True)
        function_format.setForeground(QtGui.QColor("#dcdcaa"))
        self.highlighting_rules.append((QtCore.QRegExp(r'\b[A-Za-z0-9_]+(?=\()'), function_format))

        string_format = QtGui.QTextCharFormat()
        string_format.setForeground(QtGui.QColor("#ce9178"))
        self.highlighting_rules.append((QtCore.QRegExp(r'".*?"'), string_format))
        self.highlighting_rules.append((QtCore.QRegExp(r"'.*?'"), string_format))

        comment_format = QtGui.QTextCharFormat()
        comment_format.setForeground(QtGui.QColor("#6a9955"))
        self.highlighting_rules.append((QtCore.QRegExp(r'#.*'), comment_format))

    def add_highlighting_rule(self, keywords, format):
        for word in keywords:
            self.highlighting_rules.append((QtCore.QRegExp(r'\b' + word + r'\b'), format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)