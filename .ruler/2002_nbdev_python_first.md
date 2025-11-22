# NBDev Python-First Development Checklist

## Python-First Workflow
- [ ] **Develop in Python**: Implement core logic, classes, and functions directly in `.py` files within `src/`.
- [ ] **Unit Tests**: Write standard `pytest` unit tests in `tests/` alongside your code.
- [ ] **No Auto-Export**: Do not use `#| export` or rely on notebook-to-script conversion for core library code.

## Notebooks for Examples & E2E Tests
- [ ] **Create Notebooks**: Use notebooks (`nbs/`) primarily for:
    - **End-to-End Tests**: Verifying complex flows with real components.
    - **Documentation**: Explaining how to use the API with narrative text.
    - **Visual Verification**: Inspecting outputs, charts, or media that are hard to validate in CLI tests.
- [ ] **Real Data**: Use real or realistic datasets in notebooks to demonstrate actual usage patterns.
- [ ] **Import from Library**: Import your code from the installed package (`from alma_tv.module import Class`) rather than defining it in the notebook.

## Testing Philosophy

### Core Principles
1. **Real Data**: Use actual SQLite databases (in-memory or temp files), real file structures
2. **Minimal Mocks**: Only mock external dependencies (ffprobe, network calls, hardware)
3. **Clean Up**: Tests create and destroy their own resources  
4. **Integration Over Unit**: Prefer end-to-end flows over isolated unit tests

### What to Mock
- ✅ External processes (ffprobe, media players)
- ✅ System resources (`/var/log/alma` writes, hardware devices)
- ✅ Time-dependent behavior (when testing specific dates/times)

### What NOT to Mock
- ❌ Database operations (use in-memory SQLite)
- ❌ File operations (use temp directories)
- ❌ Internal application logic

### Example: Good Test
```python
def test_scanner_integration(tmp_path: str, db_session: Session) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "Bluey_S01E01.mp4").touch()
    
    scanner = Scanner(media_root=media_dir)
    with patch.object(scanner, 'get_duration', return_value=420):
        summary = scanner.scan_directory()
    
    videos = db_session.query(Video).all()
    assert len(videos) == 1 # Should create one video
```

## Testing Discipline
- [ ] **Run Tests**: Use `uv run pytest` for fast feedback loop on logic changes.
- [ ] **Run Notebooks**: Execute notebooks to verify end-to-end integration and update documentation.
- [ ] **CI/CD**: Ensure both unit tests and notebook execution (via `nbdev_test` or similar) pass in CI.

## Documentation
- [ ] **Literate Programming**: Use markdown cells in notebooks to explain *why* something is done, not just *what*.
- [ ] **Examples**: Provide clear, copy-pasteable examples of common tasks.
- [ ] **Sync**: If you change the Python API, update the corresponding example notebooks to ensure they still run.
