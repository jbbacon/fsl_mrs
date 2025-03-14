#!/usr/bin/env python

# fsl_mrsi - wrapper script for MRSI fitting
#
# Author: Saad Jbabdi <saad@fmrib.ox.ac.uk>
#         William Carke <william.clarke@ndcn.ox.ac.uk>
#
# Copyright (C) 2019 University of Oxford

import warnings

from fsl_mrs.auxiliary import configargparse
from fsl_mrs import __version__
from fsl_mrs.utils.splash import splash
# NOTE!!!! THERE ARE MORE IMPORTS IN THE CODE BELOW (AFTER ARGPARSING)


def main():
    # Parse command-line arguments
    p = configargparse.ArgParser(
        add_config_file_help=False,
        description="FSL Magnetic Resonance Spectroscopy Imaging"
                    " Wrapper Script")

    p.add_argument('-v', '--version', action='version', version=__version__)

    required = p.add_argument_group('required arguments')
    fitting_args = p.add_argument_group('fitting options')
    optional = p.add_argument_group('additional options')

    # REQUIRED ARGUMENTS
    required.add_argument('--data',
                          required=True, type=str, metavar='<str>.NII',
                          help='input NIFTI file')
    required.add_argument('--basis',
                          required=True, type=str, metavar='<str>',
                          help='Basis file or folder')
    required.add_argument('--output',
                          required=True, type=str, metavar='<str>',
                          help='output folder')

    # FITTING ARGUMENTS
    fitting_args.add_argument('--mask',
                              type=str, metavar='<str>',
                              help='Optional NIfTI binary mask of voxels to fit.')
    fitting_args.add_argument('--algo', default='Newton', type=str,
                              help='algorithm [Newton (fast, default)'
                                   ' or MH (slow)]')
    fitting_args.add_argument('--ignore', type=str, nargs='+', metavar='METAB',
                              help='ignore certain metabolites [repeatable]')
    fitting_args.add_argument('--keep', type=str, nargs='+', metavar='METAB',
                              help='only keep these metabolites')
    fitting_args.add_argument('--combine', type=str, nargs='+',
                              action='append', metavar='METAB',
                              help='combine certain metabolites [repeatable]')
    fitting_args.add_argument('--ppmlim', default=None, type=float,
                              nargs=2, metavar=('LOW', 'HIGH'),
                              help='limit the fit optimisation to a chemical shift range. '
                                   'Defaults to a nucleus-specific range. '
                                   'For 1H default=(.2,4.2).')
    fitting_args.add_argument('--h2o', default=None, type=str, metavar='H2O',
                              help='input .H2O file for quantification')
    fitting_args.add_argument('--baseline',
                              type=str,
                              default='poly, 2',
                              help='Select baseline type. '
                                   'Options: "off", "polynomial", or "spline". '
                                   'With "polynomial" specify an order, e.g. "polynomial, 2". '
                                   'With spline specify a stiffness: '
                                   "'very-stiff', 'stiff', 'moderate', 'flexible', and 'very-flexible', "
                                   "or an effective dimension (2 -> inf) where 2 is the stiffest. "
                                   "The default is 'polynomial, 2'.")
    #     'LEGACY OPTION use --baseline instead:'
    #    ' order of baseline polynomial'
    #    ' (default=2, -1 disables)'
    fitting_args.add_argument('--baseline_order',
                              type=int,
                              default=None,
                              metavar=('ORDER'),
                              help=configargparse.SUPPRESS)
    fitting_args.add_argument('--metab_groups', default=0, nargs='+',
                              type=str_or_int_arg,
                              help="metabolite groups: list of groups or list"
                                   " of names for indept groups.")
    fitting_args.add_argument('--lorentzian', action="store_true",
                              help="Enable purely lorentzian broadening"
                                   " (default is Voigt)")
    fitting_args.add_argument('--free_shift', action="store_true",
                              help='Enable free frequency shifting of all metabolites.')
    fitting_args.add_argument('--ind_scale', default=None, type=str,
                              nargs='+',
                              help='List of basis spectra to scale'
                                   ' independently of other basis spectra.')
    fitting_args.add_argument('--disable_MH_priors', action="store_true",
                              help="Disable MH priors.")

    # ADDITONAL OPTIONAL ARGUMENTS
    optional.add_argument('--TE', type=float, default=None, metavar='TE',
                          help='Echo time for relaxation correction (ms)')
    optional.add_argument('--TR', type=float, default=None, metavar='TR',
                          help='Repetition time for relaxation correction (s)')
    optional.add_argument('--tissue_frac', type=str, nargs=3, default=None,
                          help='Tissue fraction nifti files registered to'
                               ' MRSI volume. Supplied in order: WM, GM, CSF.')
    optional.add_argument('--internal_ref', type=str, default=['Cr', 'PCr'],
                          nargs='+',
                          help='Metabolite(s) used as an internal reference.'
                               ' Defaults to tCr (Cr+PCr).')
    optional.add_argument('--wref_metabolite', type=str, default=None,
                          nargs='+',
                          help='Metabolite(s) used as an the reference for water scaling.'
                               ' Uses internal defaults otherwise.')
    optional.add_argument('--ref_protons', type=int, default=None,
                          help='Number of protons that reference metabolite is equivalent to.'
                               ' No effect without setting --wref_metabolite.')
    optional.add_argument('--ref_int_limits', type=float, default=None, nargs=2,
                          help='Reference spectrum integration limits (low, high).'
                               ' No effect without setting --wref_metabolite.')
    optional.add_argument('--h2o_scale', type=float, default=1.0,
                          help='Additional scaling modifier for external water referencing.')
    optional.add_argument('--report', action="store_true",
                          help='output html report')
    optional.add_argument('--output_correlations', action="store_true",
                          help='Output correlation matricies for each fit.')
    optional.add_argument('--verbose', action="store_true",
                          help='spit out verbose info')
    optional.add_argument('--overwrite', action="store_true",
                          help='overwrite existing output folder')
    # --single_proc is depreciated for --parallel but retained for backward compatibility
    optional.add_argument('--single_proc', action="store_true",
                          help=configargparse.SUPPRESS)
    optional.add_argument('--parallel',
                          type=str,
                          default='local',
                          help="Control parallelisation. Set to: "
                          "'off', 'local' (default), or 'cluster'. "
                          "'off' forces serial processing, "
                          "'local' parallelises over local CPUs, "
                          "'cluster' distributes over HPC SLURM nodes. "
                          "See documentation for cluster configuration.")
    optional.add_argument('--parallel-workers',
                          type=int,
                          default=None,
                          help="Number of cores (local), or workers (cluster) to use.")
    optional.add_argument('--conj_fid', action="store_true",
                          help='Force conjugation of FID')
    optional.add_argument('--no_conj_fid', action="store_true",
                          help='Forbid automatic conjugation of FID')
    optional.add_argument('--conj_basis', action="store_true",
                          help='Force conjugation of basis')
    optional.add_argument('--no_conj_basis', action="store_true",
                          help='Forbid automatic conjugation of basis')
    optional.add_argument('--no_rescale', action="store_true",
                          help='Forbid rescaling of FID/basis/H2O.')
    optional.add('--config', required=False, is_config_file=True,
                 help='configuration file')

    # Parse command-line arguments
    args = p.parse_args()

    def verboseprint(x: str):
        if args.verbose:
            print(x)

    # Output kickass splash screen
    if args.verbose:
        splash(logo='mrsi')

    # ######################################################
    # DO THE IMPORTS AFTER PARSING TO SPEED UP HELP DISPLAY
    import os
    import shutil
    import re
    import numpy as np
    from fsl_mrs.utils import report
    from fsl_mrs.core import NIFTI_MRS
    import datetime
    import nibabel as nib
    from functools import partial
    import multiprocessing as mp
    from dask.distributed import Client, progress
    from fsl_mrs.utils import misc, mrs_io
    # ######################################################

    # Check if output folder exists
    overwrite = args.overwrite
    if os.path.exists(args.output):
        if not overwrite:
            print(f"Folder '{args.output}' exists."
                  " Are you sure you want to delete it? [Y,N]")
            response = input()
            overwrite = response.upper() == "Y"
        if not overwrite:
            print('Early stopping...')
            exit()
        else:
            shutil.rmtree(args.output)
            os.mkdir(args.output)
    else:
        os.mkdir(args.output)

    # Save chosen arguments
    with open(os.path.join(args.output, "options.txt"), "w") as f:
        f.write(str(args))
        f.write("\n--------\n")
        f.write(p.format_values())

    # ######  Do the work #######

    # Read files
    mrsi_data = mrs_io.read_FID(args.data)
    if args.h2o is not None:
        H2O = mrs_io.read_FID(args.h2o)
    else:
        H2O = None

    basis = mrs_io.read_basis(args.basis)

    # Check for default MM and appropriate use of metabolite groups
    default_mm_name = re.compile(r'MM\d{2}')
    default_mm_matches = list(filter(default_mm_name.match, basis.names))
    if args.metab_groups == 0:
        default_mm_mgroups = []
    else:
        default_mm_mgroups = list(filter(default_mm_name.match, args.metab_groups))
    if len(default_mm_matches) > 0\
            and len(default_mm_mgroups) != len(default_mm_matches):
        print(f'Default macromolecules ({", ".join(default_mm_matches)}) are present in the basis set.')
        print('However they are not all listed in the --metab_groups.')
        print('It is recommended that all default MM are assigned their own group.')
        print(f'E.g. Use --metab_groups {" ".join(default_mm_matches)}')

    mrsi = mrsi_data.mrs(basis=basis,
                         ref_data=H2O)

    def loadNii(f):
        nii = np.asanyarray(nib.load(f).dataobj)
        if nii.ndim == 2:
            nii = np.expand_dims(nii, 2)
        return nii

    if args.mask is not None:
        mask = loadNii(args.mask)
        mrsi.set_mask(mask)

    if args.tissue_frac is not None:
        # WM, GM, CSF
        wm = loadNii(args.tissue_frac[0])
        gm = loadNii(args.tissue_frac[1])
        csf = loadNii(args.tissue_frac[2])
        mrsi.set_tissue_seg(csf, wm, gm)

    # Set mrs output options from MRSI class object
    mrsi.conj_FID = args.conj_fid
    mrsi.no_conj_FID = args.no_conj_fid
    mrsi.rescale = not args.no_rescale
    mrsi.keep = args.keep
    mrsi.ignore = args.ignore

    # Basis orientation
    if args.conj_basis:
        mrsi.conj_basis = True
    elif args.no_conj_basis:
        mrsi.conj_basis = False
    else:
        mrsi.check_basis(ppmlim=args.ppmlim)

    # Parse metabolite groups
    metab_groups = misc.parse_metab_groups(mrsi, args.metab_groups)

    # Store info in dictionaries to be passed to MRS and fitting
    Fitargs = {'ppmlim': args.ppmlim,
               'method': args.algo,
               'metab_groups': metab_groups}
    if args.baseline_order:
        Fitargs['baseline_order'] = args.baseline_order
    else:
        Fitargs['baseline'] = args.baseline

    if args.lorentzian and args.free_shift:
        Fitargs['model'] = 'free_shift_lorentzian'
    elif args.lorentzian:
        Fitargs['model'] = 'lorentzian'
    elif args.free_shift:
        Fitargs['model'] = 'free_shift'
    else:
        Fitargs['model'] = 'voigt'

    if args.disable_MH_priors:
        Fitargs['disable_mh_priors'] = True

    # Echo time
    if args.TE is not None:
        echotime = args.TE * 1E-3
    elif 'EchoTime' in mrsi_data.hdr_ext:
        echotime = mrsi_data.hdr_ext['EchoTime']
    else:
        echotime = None
    # Repetition time
    if args.TR is not None:
        repetition_time = args.TR
    elif 'RepetitionTime' in mrsi_data.hdr_ext:
        repetition_time = mrsi_data.hdr_ext['RepetitionTime']
    else:
        repetition_time = None

    # Fitting
    verboseprint('\n--->> Start fitting\n\n')
    verboseprint(f'    Algorithm = [{args.algo}]\n')

    # Initialise by fitting the average FID across all voxels
    verboseprint("    Initialise with average fit")
    mrs = mrsi.mrs_from_average()
    Fitargs_init = Fitargs.copy()
    Fitargs_init['method'] = 'Newton'
    res_init, _ = runvoxel([mrs, 0, None], args, Fitargs_init, echotime, repetition_time)
    Fitargs['x0'] = res_init.params

    # quick summary figure
    report.fitting_summary_fig(
        mrs,
        res_init,
        filename=os.path.join(args.output, 'fit_avg.png'))

    # Create interactive HTML report
    if args.report:
        report.create_svs_report(
            mrs,
            res_init,
            filename=os.path.join(args.output, 'report.html'),
            fidfile=args.data,
            basisfile=args.basis,
            h2ofile=args.h2o,
            date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    warnings.filterwarnings("ignore")
    func = partial(runvoxel, args=args, Fitargs=Fitargs, echotime=echotime, repetition_time=repetition_time)

    if args.parallel == "off" or args.single_proc:
        # client = Client(n_workers=1, threads_per_worker=1)
        from tqdm import tqdm
        results = list(map(func, tqdm(mrsi)))

    elif args.parallel in ("local", "cluster"):
        if args.parallel == "local":
            if args.parallel_workers:
                n_workers = args.parallel_workers
            else:
                n_workers = mp.cpu_count() - 1
            verboseprint(f'    Parallelising over {n_workers} workers ')
            client = Client(n_workers=n_workers)

        elif args.parallel == "cluster":
            if args.parallel_workers:
                n_workers = args.parallel_workers
            else:
                n_workers = 2
            verboseprint(f'    Parallelising over {n_workers} nodes ')
            from dask_jobqueue import slurm
            cluster = slurm.SLURMCluster(
                config_name='fsl_mrsi')
            cluster.scale(n_workers)

            client = Client(cluster)

        result_futures = client.map(func, mrsi)
        progress(result_futures, notebook=False)
        results = client.gather(result_futures)
    else:
        raise ValueError("--parallel should be 'off', 'local', 'cluster'.")

    # Save output files
    verboseprint(f'--->> Saving output files to {args.output}\n')

    # Results --> Images
    # Store concentrations, uncertainties, residuals, predictions
    # Output:
    # 1) concs - folders with N_metabs x 3D nifti for each scaling
    #    (raw,internal,molarity,molality)
    # 2) uncertainties - N_metabs x 3D nifti as percentage
    # 3) qc - 2 x N_metabs x 3D nifti for SNR and fwhm
    # 4) fit - predicted, residuals and baseline?

    # Generate the folders
    concs_folder = os.path.join(args.output, 'concs')
    uncer_folder = os.path.join(args.output, 'uncertainties')
    nuisance_folder = os.path.join(args.output, 'nuisance')
    qc_folder = os.path.join(args.output, 'qc')
    fit_folder = os.path.join(args.output, 'fit')
    misc_folder = os.path.join(args.output, 'misc')

    os.mkdir(concs_folder)
    os.mkdir(uncer_folder)
    os.mkdir(nuisance_folder)
    os.mkdir(qc_folder)
    os.mkdir(fit_folder)
    os.mkdir(misc_folder)

    # Extract concentrations
    indicies = [res[1] for res in results]
    scalings = ['raw']
    if results[0][0].concScalings['internal'] is not None:
        scalings.append('internal')
    if results[0][0].concScalings['molarity'] is not None:
        scalings.append('molarity')
    if results[0][0].concScalings['molality'] is not None:
        scalings.append('molality')

    def save_img_output(fname, data):
        if data.ndim > 3 and data.shape[3] == mrsi.FID_points:
            NIFTI_MRS(data, header=mrsi_data.header).save(fname)
        else:
            img = nib.Nifti1Image(data, mrsi_data.voxToWorldMat)
            nib.save(img, fname)

    metabs = results[0][0].metabs
    for scale in scalings:
        cur_fldr = os.path.join(concs_folder, scale)
        os.mkdir(cur_fldr)
        for metab in metabs:
            metab_conc_list = [res[0].getConc(scaling=scale, metab=metab)
                               for res in results]

            file_nm = os.path.join(cur_fldr, metab + '.nii.gz')
            save_img_output(file_nm,
                            mrsi.list_to_matched_array(
                                metab_conc_list,
                                indicies=indicies,
                                cleanup=True,
                                dtype=float))

    # Uncertainties
    for metab in results[0][0].metabs:
        metab_sd_list = [res[0].getUncertainties(metab=metab)
                         for res in results]
        file_nm = os.path.join(uncer_folder, metab + '_sd.nii.gz')
        save_img_output(file_nm,
                        mrsi.list_to_matched_array(
                            metab_sd_list,
                            indicies=indicies,
                            cleanup=True,
                            dtype=float))

    # Fitting nuisance parameters
    # Phases - p0, p1
    p0_list = [res[0].getPhaseParams()[0] for res in results]
    file_p0 = os.path.join(nuisance_folder, 'p0.nii.gz')
    save_img_output(file_p0,
                    mrsi.list_to_matched_array(
                        p0_list,
                        indicies=indicies,
                        cleanup=False,
                        dtype=float))

    p1_list = [res[0].getPhaseParams()[1] for res in results]
    file_p1 = os.path.join(nuisance_folder, 'p1.nii.gz')
    save_img_output(file_p1,
                    mrsi.list_to_matched_array(
                        p1_list,
                        indicies=indicies,
                        cleanup=False,
                        dtype=float))

    # Grouped - shifts, widths (gamma, sigma, combined)
    for group in range(results[0][0].g):
        shiftn_list = [res[0].getShiftParams()[group] for res in results]
        file_sn = os.path.join(nuisance_folder, f'shift_group{group}.nii.gz')
        save_img_output(file_sn,
                        mrsi.list_to_matched_array(
                            shiftn_list,
                            indicies=indicies,
                            cleanup=False,
                            dtype=float))

        comb_n_list = [res[0].getLineShapeParams()[0][group] for res in results]
        file_comb = os.path.join(nuisance_folder, f'combined_lw_group{group}.nii.gz')
        save_img_output(file_comb,
                        mrsi.list_to_matched_array(
                            comb_n_list,
                            indicies=indicies,
                            cleanup=False,
                            dtype=float))

        gamma_n_list = [res[0].getLineShapeParams()[1][group] for res in results]
        file_gam = os.path.join(nuisance_folder, f'gamma_group{group}.nii.gz')
        save_img_output(file_gam,
                        mrsi.list_to_matched_array(
                            gamma_n_list,
                            indicies=indicies,
                            cleanup=False,
                            dtype=float))

        if results[0][0].model == 'voigt':
            sigma_n_list = [res[0].getLineShapeParams()[2][group] for res in results]
            file_sig = os.path.join(nuisance_folder, f'sigma_group{group}.nii.gz')
            save_img_output(file_sig,
                            mrsi.list_to_matched_array(
                                sigma_n_list,
                                indicies=indicies,
                                cleanup=False,
                                dtype=float))

    # qc - SNR & FWHM
    for metab in results[0][0].original_metabs:
        metab_fwhm_list = [res[0].getQCParams(metab=metab)[1]
                           for res in results]
        file_nm = os.path.join(qc_folder, metab + '_fwhm.nii.gz')
        save_img_output(file_nm,
                        mrsi.list_to_matched_array(
                            metab_fwhm_list,
                            indicies=indicies,
                            cleanup=True,
                            dtype=float))

        metab_snr_list = [res[0].getQCParams(metab=metab)[0]
                          for res in results]
        file_nm = os.path.join(qc_folder, metab + '_snr.nii.gz')
        save_img_output(file_nm,
                        mrsi.list_to_matched_array(
                            metab_snr_list,
                            indicies=indicies,
                            cleanup=True,
                            dtype=float))

    # fit
    mrs_scale = mrsi.get_scalings_in_order()
    pred_list = []
    for res, scale in zip(results, mrs_scale):
        pred_list.append(res[0].pred / scale['FID'])
    file_nm = os.path.join(fit_folder, 'fit.nii.gz')
    save_img_output(file_nm,
                    mrsi.list_to_matched_array(
                        pred_list,
                        indicies=indicies,
                        cleanup=False,
                        dtype=np.complex64))

    res_list = []
    for res, scale in zip(results, mrs_scale):
        res_list.append(res[0].residuals / scale['FID'])
    file_nm = os.path.join(fit_folder, 'residual.nii.gz')
    save_img_output(file_nm,
                    mrsi.list_to_matched_array(
                        res_list,
                        indicies=indicies,
                        cleanup=False,
                        dtype=np.complex64))

    baseline_list = []
    for res, scale in zip(results, mrs_scale):
        baseline_list.append(res[0].baseline / scale['FID'])
    file_nm = os.path.join(fit_folder, 'baseline.nii.gz')
    save_img_output(file_nm,
                    mrsi.list_to_matched_array(
                        baseline_list,
                        indicies=indicies,
                        cleanup=False,
                        dtype=np.complex64))

    # Save a parameter mappings of:
    # 1) metabolites to groups
    results[0][0].metab_in_group_json(
        os.path.join(misc_folder, 'metabolite_groups.json'))

    # 2) A list of parameters (to go with the correlation matrix)
    results[0][0].fit_parameters_json(
        os.path.join(misc_folder, 'mrs_fit_parameters.json'))

    if args.output_correlations:
        # Per voxel correlations of parameters
        corr_list = [res[0].corr for res in results]
        corr_mats = mrsi.list_to_correlation_array(
            corr_list,
            indicies=indicies,
            cleanup=True)
        # Save
        file_nm = os.path.join(misc_folder, 'fit_correlations.nii.gz')
        corr_img = nib.Nifti1Image(corr_mats, mrsi_data.voxToWorldMat)
        corr_img.header.set_intent(
            1005,  # NIFTI_INTENT_SYMMATRIX
            params=(corr_list[0].shape[0], ),
            name='MRS fit correlation matrix')
        nib.save(corr_img, file_nm)

    verboseprint('\n\n\nDone.')


def runvoxel(mrs_in, args, Fitargs, echotime, repetition_time):
    from fsl_mrs.utils import fitting, quantify

    mrs, index, tissue_seg = mrs_in
    try:
        res = fitting.fit_FSLModel(mrs, **Fitargs)

        # Internal and Water quantification if requested
        if (mrs.H2O is None) or (echotime is None) or (repetition_time is None):
            if mrs.H2O is not None and echotime is None:
                warnings.warn(
                    'H2O file provided but could not determine TE:'
                    ' no absolute quantification will be performed.',
                    UserWarning)
            if mrs.H2O is not None and repetition_time is None:
                warnings.warn(
                    'H2O file provided but could not determine TR:'
                    ' no absolute quantification will be performed.',
                    UserWarning)
            res.calculateConcScaling(mrs, internal_reference=args.internal_ref, verbose=args.verbose)
        else:
            # Form quantification information
            q_info = quantify.QuantificationInfo(
                echotime,
                repetition_time,
                mrs.names,
                mrs.centralFrequency / 1E6,
                water_ref_metab=args.wref_metabolite,
                water_ref_metab_protons=args.ref_protons,
                water_ref_metab_limits=args.ref_int_limits)

            if tissue_seg:
                q_info.set_fractions(tissue_seg)
            if args.h2o_scale:
                q_info.add_corr = args.h2o_scale

            res.calculateConcScaling(
                mrs,
                quant_info=q_info,
                internal_reference=args.internal_ref,
                verbose=args.verbose)
        # Combine metabolites.
        if args.combine is not None:
            res.combine(args.combine)
    except Exception as exc:
        print(f'Exception ({exc}) occured in index {index}.')
        raise exc

    return res, index


def str_or_int_arg(x):
    try:
        return int(x)
    except ValueError:
        return x


if __name__ == '__main__':
    main()
