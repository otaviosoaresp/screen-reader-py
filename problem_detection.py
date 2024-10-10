import re
import nltk

nltk.download('punkt', quiet=True)

def is_alg_problem(text):
    return has_keywords(text) or has_patterns(text) or has_token_matches(text)

def has_keywords(text):
    keywords = [
        'input', 'output', 'example', 'constraint', 'integer', 'array', 'list', 'string',
        'tree', 'graph', 'algorithm', 'compute', 'calculate', 'determine', 'find', 'search',
        'maximum', 'minimum', 'optimize', 'sort', 'sequence', 'data structure',
        'dynamic programming', 'recursion', 'complexity', 'efficient', 'function', 'test case'
    ]
    return any(re.search(rf'\b{keyword}\b', text, re.IGNORECASE) for keyword in keywords)

def has_patterns(text):
    patterns = [
        r'Constraints?:', r'Input\s+Format:', r'Output\s+Format:', r'Sample\s+Input:',
        r'Sample\s+Output:', r'Examples?:', r'Description:', r'Problem\s+Statement:',
        r'You are given', r'Write a program', r'Given an? .*?, (determine|compute|find|calculate)',
        r'In this problem', r'The first line contains', r'Read an integer', r'For each test case',
        r'Print .*? to stdout', r'Explanation', r'Note:', r'Test\s+Cases?', r'Function Description',
        r'Complete the .*? function', r'Return the .*?', r'Your task is to', r'Limits?:',
        r'Input consists of', r'Output consists of', r'Constraints:', r'Objective:', r'Challenge:',
        r'Background:', r'Compute the', r'Find the', r'Calculate the', r'Determine the',
        r'Implement an algorithm', r'Solve the following', r'Consider the following',
        r'Assume that', r'Suppose that', r'Let\'s define', r'Let us define', r'It is required to',
        r'Develop a function', r'Provide an algorithm', r'Design a program', r'Your function should',
        r'Return YES if', r'Return NO if', r'Constraints are as follows', r'The goal is to',
        r'Under the following conditions', r'Examples? \(input/output\):', r'All input numbers are',
        r'The input data is guaranteed to be', r'The output should be', r'Output Format:',
        r'Input Format:'
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

def has_token_matches(text):
    tokens = nltk.word_tokenize(text.lower())
    keywords = {
        'compute', 'calculate', 'determine', 'find', 'output', 'input', 'integer', 'array',
        'string', 'given', 'write', 'program', 'function', 'algorithm', 'return', 'constraints',
        'test', 'case', 'example', 'data', 'structure', 'efficient', 'complexity', 'optimize',
        'search', 'sort', 'maximum', 'minimum', 'number', 'list', 'tree', 'graph', 'node',
        'edge', 'dynamic', 'programming', 'recursion', 'solution', 'implement', 'design',
        'develop', 'code', 'procedure', 'method', 'approach', 'logic', 'problem', 'statement',
        'task', 'objective', 'goal', 'challenge', 'operation', 'process', 'step', 'sequence',
        'order', 'condition', 'loop', 'iteration', 'recurrence', 'formula', 'equation',
        'expression', 'variable', 'parameter', 'argument', 'sample', 'constraint', 'limit',
        'bound', 'time', 'space', 'efficiency', 'performance', 'optimize', 'improve',
        'increase', 'decrease', 'maximize', 'minimize'
    }
    return len(keywords.intersection(set(tokens))) >= 3