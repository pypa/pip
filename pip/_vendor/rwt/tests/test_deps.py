import pkg_resources

from rwt import deps

def test_entry_points():
	"""
	Ensure entry points are visible after making packages visible
	"""
	with deps.on_sys_path('jaraco.mongodb'):
		eps = pkg_resources.iter_entry_points('pytest11')
		assert list(eps), "Entry points not found"
