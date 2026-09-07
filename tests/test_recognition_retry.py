"""Retry presets are explicit, cancellable, full-resolution and non-destructive."""

from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from threading import Event
from unittest.mock import patch

import pytest
from PIL import Image
from rdkit import Chem
from rdkit.Chem import AllChem

from molrecognizer.core.molecule import Molecule
from molrecognizer.core.recognition_retry import RETRY_PROFILES, recognition_alternatives
from molrecognizer.core.recognizer import OSRARecognizer, RecognitionCancelled
from tests.test_history import _molecular_state
from tests.test_shutdown import _run


def _source():
    source = Chem.MolFromSmiles("C[C@H](N)c1ccccc1")
    AllChem.Compute2DCoords(source)
    Chem.WedgeMolBonds(source, source.GetConformer())
    source.SetProp("Confidence_estimate", "4.276")
    return source


def _sdf(mol):
    return (Chem.MolToMolBlock(mol) + "\n> <Confidence_estimate>\n"
            + mol.GetProp("Confidence_estimate") + "\n\n$$$$\n").encode()


def test_retry_presets_keep_full_resolution_and_sdf_geometry(tmp_path):
    source = _source()
    expected = Molecule.from_rdkit(source)
    image = Image.new('RGB', (777, 333), (123, 45, 67))
    original_pixels = image.tobytes()
    paths, status = [], []

    def run(command, **kwargs):
        index = len(paths)
        path = Path(command[-1])
        paths.append(path)
        assert command[1:3] == ['-f', 'sdf']
        assert command[command.index('--timeout') + 1] == '15'
        assert command[5:-2] == [*RETRY_PROFILES[index].options, '-p']
        assert kwargs['timeout'] == 25
        with Image.open(path) as stored:
            assert stored.size == image.size
            assert stored.tobytes() == original_pixels
        return CompletedProcess([], 15, _sdf(source), b'')

    with patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra'), \
         patch('molrecognizer.core.recognizer.subprocess.run', side_effect=run):
        candidates = list(recognition_alternatives(image, OSRARecognizer(), status.append))
    assert [c.name for c in candidates] == [p.name for p in RETRY_PROFILES]
    assert len(status) == 3 and len(paths) == 3 and len(set(paths)) == 1
    assert not paths[0].exists() and image.tobytes() == original_pixels
    for candidate in candidates:
        assert candidate.confidence == 4.276 and not candidate.error
        assert candidate.molecule.get_all_bonds() == expected.get_all_bonds()
        for actual, original in zip(candidate.molecule.get_2d_coords(), expected.get_2d_coords()):
            assert actual == pytest.approx(original, abs=1e-4)


def test_failed_attempts_do_not_discard_other_candidates():
    paths = []
    def run(command, **kwargs):
        paths.append(Path(command[-1]))
        if len(paths) == 1:
            raise TimeoutExpired(command, 25)
        if len(paths) == 2:
            return CompletedProcess([], 1, b'', b'No structure')
        source = _source()
        source.SetProp('Confidence_estimate', 'nan')
        return CompletedProcess([], 0, _sdf(source), b'')
    with patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra'), \
         patch('molrecognizer.core.recognizer.subprocess.run', side_effect=run):
        result = list(recognition_alternatives(Image.new('RGB', (20, 20)), OSRARecognizer()))
    assert result[0].error and result[1].error
    assert result[2].molecule is not None and result[2].confidence is None
    assert not paths[-1].exists()


def test_cancellation_between_attempts_removes_image_and_stops_work():
    cancelled = Event()
    paths = []
    def run(command, **kwargs):
        paths.append(Path(command[-1]))
        return CompletedProcess([], 0, _sdf(_source()), b'')
    with patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra'):
        recognizer = OSRARecognizer(cancel_event=cancelled)
    with patch.object(recognizer, '_run_osra', side_effect=run):
        attempts = recognition_alternatives(Image.new('RGB', (20, 20)), recognizer)
        assert next(attempts).molecule is not None
        assert paths[0].is_file()
        cancelled.set()
        with pytest.raises(RecognitionCancelled):
            next(attempts)
        assert len(paths) == 1 and not paths[0].exists()


def test_replacement_command_preserves_history_and_candidate():
    from molrecognizer.editor.history import (
        ChangeElementCommand, HistoryManager, ReplaceMoleculeCommand,
    )
    mol = Molecule.from_rdkit(_source())
    initial = _molecular_state(mol)
    history = HistoryManager(mol)
    history.execute(ChangeElementCommand(2, 'O'))
    edited = _molecular_state(mol)
    candidate = Molecule.from_rdkit(_source())
    candidate.set_atom_position(0, 7, 9)
    chosen = _molecular_state(candidate)
    history.execute(ReplaceMoleculeCommand(candidate))
    assert _molecular_state(mol) == chosen
    history.undo()
    assert _molecular_state(mol) == edited
    history.undo()
    assert _molecular_state(mol) == initial
    history.redo()
    history.redo()
    assert _molecular_state(mol) == chosen
    assert _molecular_state(candidate) == chosen


def test_preview_never_applies_or_auto_selects_highest_score(tmp_path):
    _run(tmp_path, """
        from PySide6.QtGui import QPixmap
        from molrecognizer.gui.recognition_review import RecognitionReviewDialog
        from molrecognizer.core.recognition_retry import RecognitionCandidate
        from molrecognizer.core.smiles import smiles_to_molecule
        from tests.test_history import _molecular_state

        source = QPixmap(1200, 800)
        source.fill(Qt.GlobalColor.white)
        current = smiles_to_molecule('CCO')
        before = _molecular_state(current)
        dialog = RecognitionReviewDialog(source, current, window)
        dialog.open()
        app.processEvents()
        for name, score, smiles in [('First', 1, 'CN'), ('Second', 999, 'C1CCCCC1')]:
            dialog.add_candidate(RecognitionCandidate(name, smiles_to_molecule(smiles), score))
        dialog.add_candidate(RecognitionCandidate('Failed', error='No structure'))
        assert dialog._choices.currentRow() == 0
        assert dialog.selected_candidate is None and not dialog._use.isEnabled()
        assert dialog._source_view.scene().items()[0].pixmap().size() == source.size()
        dialog._choices.setCurrentRow(1)
        assert dialog._smiles.text() == 'CN'
        assert dialog.selected_candidate.name == 'First'
        assert dialog._use.isEnabled()
        dialog.add_candidate(RecognitionCandidate('Later', smiles_to_molecule('CCN'), 9999))
        assert dialog._choices.currentRow() == 1
        assert _molecular_state(current) == before
        dialog._choices.setCurrentRow(3)
        assert not dialog._use.isEnabled() and dialog.selected_candidate is None
        dialog.finish()
        dialog.grab().save(str(Path(sys.argv[1]) / 'recognition-review.png'))
        dialog.reject()
        assert _molecular_state(current) == before
        # An initial recognition failure leaves no current structure: still
        # require explicit selection, even when the first result arrives.
        empty = RecognitionReviewDialog(source, None, window)
        empty.open()
        app.processEvents()
        empty.add_candidate(RecognitionCandidate('First', smiles_to_molecule('CN'), 999))
        assert empty._choices.currentRow() == -1 and not empty._use.isEnabled()
        empty.reject()
        window.close()
    """)


def test_retry_apply_is_explicit_and_undoable_in_main_window(tmp_path):
    _run(tmp_path, """
        from molrecognizer.core.smiles import smiles_to_molecule
        from molrecognizer.core.recognizer import OSRARecognizer
        from molrecognizer.editor.history import ChangeElementCommand
        from tests.test_history import _molecular_state
        from tests.test_recognition_retry import _source
        window._set_molecule(smiles_to_molecule('CCO'))
        window._editor._history.execute(ChangeElementCommand(2, 'N'))
        window._editor._set_tool('select')
        window._editor._current_tool._selected = {0, 1, 2}
        window._editor._current_tool._highlight_selection()
        before = _molecular_state(window._molecule)
        window._recognition_image = Image.new('RGB', (900, 500), 'white')
        window._update_retry_available()
        assert window._left_panel._retry_btn.isEnabled()
        assert window._menu_actions['Retry recognition…'].isEnabled()
        patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra').start()
        patch.object(OSRARecognizer, '_read_sdf', side_effect=lambda *a, **k: _source()).start()
        window._left_panel._retry_btn.click()
        dialog = window._retry_dialog
        assert dialog is not None and not window._left_panel._retry_btn.isEnabled()
        until(lambda: window._retry_worker is None)
        assert len(dialog._candidates) == 4
        assert _molecular_state(window._molecule) == before
        dialog._choices.setCurrentRow(1)
        assert _molecular_state(window._molecule) == before
        selected = _molecular_state(dialog.selected_candidate.molecule)
        window._mol_3d = object()
        dialog._use.click()
        assert window._retry_dialog is None
        assert _molecular_state(window._molecule) == selected
        assert window._mol_3d is None
        assert not window._editor._current_tool._selected
        window._editor._current_tool._selected = {0, window._molecule.num_atoms - 1}
        window._editor._current_tool._highlight_selection()
        window._editor._undo()
        assert not window._editor._current_tool._selected
        assert _molecular_state(window._molecule) == before
        window._editor._undo()
        assert window._bottom_bar.smiles_text == 'CCO'
        window._editor._redo()
        window._editor._redo()
        assert _molecular_state(window._molecule) == selected
        assert window._left_panel._retry_btn.isEnabled()
        window._on_clear_all()
        assert window._recognition_image is None
        assert not window._left_panel._retry_btn.isEnabled()
        window.close()
    """)


@pytest.mark.parametrize('close_window', [False, True])
def test_cancel_or_close_kills_active_retry_and_removes_temp_image(tmp_path, close_window):
    _run(tmp_path, f"""
        import subprocess
        from molrecognizer.core.smiles import smiles_to_molecule
        from tests.test_history import _molecular_state
        children, images = [], []
        original_popen = subprocess.Popen
        def slow_osra(command, **kwargs):
            images.append(Path(command[-1]))
            process = original_popen([sys.executable, '-c', 'import time; time.sleep(60)'], **kwargs)
            children.append(process)
            return process
        patch('molrecognizer.core.recognizer.shutil.which', return_value=sys.executable).start()
        patch('molrecognizer.core.recognizer.subprocess.Popen', slow_osra).start()
        window._set_molecule(smiles_to_molecule('CCO'))
        before = _molecular_state(window._molecule)
        window._recognition_image = Image.new('RGB', (260, 179), 'white')
        window._on_retry_recognition()
        dialog = window._retry_dialog
        until(lambda: bool(children))
        assert images[0].is_file()
        start = time.monotonic()
        if {close_window!r}:
            timed_out = []
            watchdog = QTimer()
            watchdog.setSingleShot(True)
            watchdog.timeout.connect(lambda: (timed_out.append(True), app.quit()))
            watchdog.start(3000)
            QTimer.singleShot(0, window.close)
            app.exec()
            assert not timed_out, 'Closing must exit the actual application event loop'
            assert time.monotonic() - start < 2
        else:
            dialog.reject()
            assert time.monotonic() - start < .5
        until(lambda: window._retry_worker is None)
        assert window._retry_dialog is None
        assert children[0].poll() is not None
        assert len(children) == 1 and not images[0].exists()
        assert _molecular_state(window._molecule) == before
        if {close_window!r}:
            assert not window.isVisible()
        else:
            assert window.isVisible() and window._left_panel._retry_btn.isEnabled()
        errors.assert_not_called()
        warnings.assert_not_called()
        window.close()
    """)


def test_retry_available_after_initial_failure_and_keeps_original_pixels(tmp_path):
    _run(tmp_path, """
        from molrecognizer.core.recognizer import OSRARecognizer
        fake = patch('molrecognizer.core.recognizer.MoleculeRecognizer').start()
        fake.return_value.recognize.side_effect = ValueError('Initial recognition failed')
        image = Image.new('RGB', (987, 654), (12, 34, 56))
        window._recognize_image(image)
        assert not window._left_panel._retry_btn.isEnabled()
        image.putpixel((0, 0), (255, 0, 0))
        until(lambda: window._worker is None)
        assert window._recognition_image.size == (987, 654)
        assert window._recognition_image.getpixel((0, 0)) == (12, 34, 56)
        assert window._left_panel._retry_btn.isEnabled()
        errors.assert_called_once()
        patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra').start()
        patch.object(OSRARecognizer, '_read_sdf', return_value=None).start()
        window._on_retry_recognition()
        dialog = window._retry_dialog
        until(lambda: window._retry_worker is None)
        assert len(dialog._candidates) == 3
        assert all(c.error for c in dialog._candidates)
        assert not dialog._use.isEnabled()
        assert 'No usable alternatives' in dialog._status.text()
        assert window._molecule is None
        dialog.reject()
        window.close()
    """)


def test_stop_preserves_completed_candidates_for_review(tmp_path):
    _run(tmp_path, """
        from molrecognizer.core.recognizer import OSRARecognizer, RecognitionCancelled
        from molrecognizer.core.smiles import smiles_to_molecule
        from tests.test_history import _molecular_state
        from tests.test_recognition_retry import _source
        calls = []
        def read(recognizer, path, **kwargs):
            calls.append(path)
            if len(calls) == 1:
                return _source()
            # Simulate a cancellable second attempt while keeping the first.
            assert recognizer._cancel_event.wait(5), 'Expected Stop retries'
            raise RecognitionCancelled()
        patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra').start()
        patch.object(OSRARecognizer, '_read_sdf', read).start()
        window._set_molecule(smiles_to_molecule('CCO'))
        before = _molecular_state(window._molecule)
        window._recognition_image = Image.new('RGB', (260, 179), 'white')
        window._on_retry_recognition()
        dialog = window._retry_dialog
        until(lambda: len(calls) == 2 and len(dialog._candidates) == 2)
        dialog._stop.click()
        until(lambda: window._retry_worker is None)
        assert dialog.isVisible() and not dialog._stop.isEnabled()
        assert 'Retries stopped' in dialog._status.text()
        assert len(dialog._candidates) == 2 and len(calls) == 2
        assert not calls[0].exists()
        assert _molecular_state(window._molecule) == before
        dialog._choices.setCurrentRow(1)
        dialog._use.click()
        assert _molecular_state(window._molecule) != before
        window._editor._undo()
        assert _molecular_state(window._molecule) == before
        window.close()
    """)
