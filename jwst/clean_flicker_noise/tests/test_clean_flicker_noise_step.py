import logging
import os

import pytest
from stdatamodels.jwst import datamodels

from jwst.clean_flicker_noise import CleanFlickerNoiseStep
from jwst.clean_flicker_noise.tests.test_clean_flicker_noise import (
    make_small_ramp_model, make_nirspec_fs_model)
from jwst.tests.helpers import LogWatcher


@pytest.fixture
def log_watcher(monkeypatch):
    # Set a log watcher to check for a log message at any level
    # in CleanFlickerNoiseStep
    watcher = LogWatcher('')
    logger = logging.getLogger('stpipe.CleanFlickerNoiseStep')
    for level in ['debug', 'info', 'warning', 'error']:
        monkeypatch.setattr(logger, level, watcher)
    return watcher


@pytest.mark.parametrize('skip', [True, False])
def test_output_type(skip):
    input_model = make_small_ramp_model()
    cleaned = CleanFlickerNoiseStep.call(input_model, skip=skip)

    # output is a ramp model either way
    assert isinstance(cleaned, datamodels.RampModel)

    # status may be SKIPPED or COMPLETE
    if skip:
        assert cleaned.meta.cal_step.clean_flicker_noise == 'SKIPPED'
    else:
        assert cleaned.meta.cal_step.clean_flicker_noise == 'COMPLETE'

    input_model.close()
    cleaned.close()


def test_save_mask(tmp_path):
    input_model = make_small_ramp_model()
    input_model.meta.filename = 'test_jump.fits'

    output_dir = str(tmp_path)
    cleaned = CleanFlickerNoiseStep.call(
        input_model, skip=False, save_mask=True, output_dir=output_dir)

    mask_file = str(tmp_path / 'test_mask.fits')
    assert os.path.isfile(mask_file)

    mask_model = datamodels.open(mask_file)
    assert isinstance(mask_model, datamodels.ImageModel)

    input_model.close()
    cleaned.close()
    mask_model.close()


def test_save_background(tmp_path):
    input_model = make_small_ramp_model()
    input_model.meta.filename = 'test_jump.fits'

    output_dir = str(tmp_path)
    cleaned = CleanFlickerNoiseStep.call(
        input_model, skip=False, save_background=True, output_dir=output_dir)

    bkg_file = str(tmp_path / 'test_flicker_bkg.fits')
    assert os.path.isfile(bkg_file)

    bkg_model = datamodels.open(bkg_file)
    assert isinstance(bkg_model, datamodels.RampModel)

    input_model.close()
    cleaned.close()
    bkg_model.close()


def test_save_noise(tmp_path):
    input_model = make_small_ramp_model()
    input_model.meta.filename = 'test_jump.fits'

    output_dir = str(tmp_path)
    cleaned = CleanFlickerNoiseStep.call(
        input_model, skip=False, save_noise=True, output_dir=output_dir)

    noise_file = str(tmp_path / 'test_flicker_noise.fits')
    assert os.path.isfile(noise_file)

    noise_model = datamodels.open(noise_file)
    assert isinstance(noise_model, datamodels.RampModel)

    input_model.close()
    cleaned.close()
    noise_model.close()


def test_apply_flat(log_watcher):
    input_model = make_small_ramp_model()

    log_watcher.message = 'Using FLAT'
    cleaned = CleanFlickerNoiseStep.call(input_model, skip=False, apply_flat_field=True)
    log_watcher.assert_seen()

    # Flat file was used, but flat_field step was not applied
    assert cleaned.meta.ref_file.flat.name is not None
    assert cleaned.meta.cal_step.flat_field is None

    input_model.close()
    cleaned.close()


def test_apply_flat_not_available(log_watcher):
    input_model = make_nirspec_fs_model()

    log_watcher.message = 'Flat correction is not available'
    cleaned = CleanFlickerNoiseStep.call(input_model, skip=False, apply_flat_field=True)
    log_watcher.assert_seen()

    # Flat file was not used but step proceeded
    assert cleaned.meta.ref_file.flat.name == 'N/A'

    input_model.close()
    cleaned.close()
