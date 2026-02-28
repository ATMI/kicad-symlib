import re
from typing import Any, Iterator, List, Optional, Tuple

class KiCadSymLibraryParser:
	ARG_SPLIT = re.compile(r'"[^"]+"|\S+')

	class Node:
		def __init__(self, args: str, children: List[Optional['KiCadSymLibraryParser.Node']] = None):
			super().__init__()
			pieces = KiCadSymLibraryParser.ARG_SPLIT.findall(args)
			self.tag: str = pieces[0]
			self.attributes: List[str] = pieces[1:]
			self.children: List[Optional['KiCadSymLibraryParser.Node']] = children if children else []

		def get_tag(self) -> str:
			return self.tag

		def get_attributes(self) -> List[str]:
			return self.attributes

		def set_attributes(self, attributes: List[Any]) -> None:
			self.attributes = [str(x) for x in attributes]

		def get_children(self) -> List[Optional['KiCadSymLibraryParser.Node']]:
			return self.children

		def select_children(self, tag: str) -> Iterator:
			for child in self.children:
				if child.get_tag() == tag:
					yield child

		def remove_children(self, tags: List[str]) -> None:
			to_delete: List[Optional['KiCadSymLibraryParser.Node']] = []
			for child in self.get_children():
				if child.get_tag() in tags:
					to_delete.append(child)
			for child in to_delete:
				self.children.remove(child)

		def get_child(self, tag: str) -> Optional['KiCadSymLibraryParser.Node']:
			selected: List[KiCadSymLibraryParser.Node] = [x for x in self.select_children(tag)]
			if len(selected) > 1:
				raise ValueError(f"tag '{tag}' is not unique: " + ", ".join(map(lambda x: x.attributes[0], selected)))
			if len(selected) > 0:
				return selected[0]
			return None

		@staticmethod
		def to_bool(string: str) -> bool:
			match string:
				case 'yes':
					return True
				case 'no':
					return False
				case _:
					raise ValueError(string)

		def __str__(self):
			return self.get_tag()

		def print(self, level: int, output) -> None:
			print(f"{'  ' * level}({self.get_tag()} {' '.join(self.attributes)}", file=output, end='')
			if len(self.children) > 0:
				print(file=output)
				for child in self.children:
					child.print(level + 1, output)
				print(f"{'  ' * level}", file=output, end='')
			print(')', file=output)

	def __init__(self, filepath: str):
		super().__init__()
		self.filepath: str = filepath
		with open(self.filepath, 'r') as file:
			import re
			content = re.sub(r'\s+', ' ', file.read().strip(' \t\n\r')).replace(' )', ')')
		if not self.check_brackets(content):
			raise ValueError(f"invalid KiCad symbol, unbalanced brackets in file: {self.filepath}")
		m = self.match_brackets(content[1:-1], 0, len(content) - 2)
		self.tree: KiCadSymLibraryParser.Node = m[0]
		if self.tree.get_tag() != 'kicad_symbol_lib':
			raise ValueError(f"invalid KiCad symbol library root: {self.tree.get_tag()}")
		if len(self.tree.get_attributes()) != 0:
			raise ValueError(f"unexpected KiCad symbol library attributes: {" ".join(self.tree.get_attributes())}")

	@staticmethod
	def check_brackets(string: str) -> bool:
		if not string:
			return False
		if len(string) < 2:
			return False
		if string[0] != '(':
			return False
		if string[-1] != ')':
			return False
		balance: int = 0
		for char in string[1:-1]:
			if char == '(':
				balance += 1
			elif char == ')':
				balance -= 1
		if balance != 0:
			return False
		return True

	@staticmethod
	def match_brackets(string: str, begin: int, end: int) -> Tuple[Node, int] | None:
		children: List[KiCadSymLibraryParser.Node] = []
		m = -1
		i = begin
		while i < end:
			if string[i] == '(':
				if m < 0:
					m = i
				child, i = KiCadSymLibraryParser.match_brackets(string, i + 1, end)
				children.append(child)
			elif string[i] == ')':
				if m < 0:
					m = i
				break
			i += 1
		return KiCadSymLibraryParser.Node(string[begin:m], children), i
