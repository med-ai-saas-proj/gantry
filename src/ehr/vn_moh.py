# AI generated from sql.py

from typing import Optional, TypedDict
from datetime import datetime
from dataclasses import dataclass
from collections.abc import Iterable


class TrangThaiKcb(TypedDict, total=False):
    """Represents the status of a medical examination/treatment episode."""

    ma_lk: str  # Foreign key linking to KcbTongHop.
    stt: int  # Sequential number, increments from 1 for each data submission.
    ma_bn: str  # Patient ID as per the healthcare facility's regulations.
    ho_ten: str  # Full name of the patient.
    so_cccd: str  # National ID, citizen ID, or passport number of the patient.
    ngay_sinh: str  # Date and time of birth (yyyymmddHHmm).
    gioi_tinh: int  # Gender code (1: Male; 2: Female; 3: Undetermined).
    ma_the_bhyt: str  # Patient's health insurance card number.
    ma_dkbd: str  # Code of the initial registration facility.
    gt_the_tu: str  # Health insurance card start date (yyyymmdd).
    gt_the_den: str  # Health insurance card end date (yyyymmdd).
    ma_doituong_kcb: int  # Patient category code.
    ngay_vao: str  # Time the patient arrived at the facility (yyyymmddHHmm).
    ma_loai_kcb: int  # Type of medical care code.
    ma_cskcb: str  # Code of the facility where the patient is being treated.
    ma_dich_vu: str  # Code for the technical or examination service.
    ten_dich_vu: str  # Name of the technical or examination service.
    ngay_yl: str  # Time of the medical order (yyyymmddHHmm).


class KcbTongHop(TypedDict, total=False):
    """Represents a general medical examination/treatment record."""

    ma_lk: (
        str  # Unique treatment episode code, used to link tables. (PRIMARY KEY)
    )
    ma_bn: str  # Patient ID as per the healthcare facility's regulations.
    ho_ten: str  # Full name of the patient.
    stt: int  # Sequential number, increments from 1 for each data submission.
    so_cccd: str  # National ID, citizen ID, or passport number.
    ngay_sinh: str  # Patient's date of birth (yyyymmddHHMM).
    gioi_tinh: int  # Gender code (1: Male, 2: Female, 3: Undetermined).
    ma_quoctich: str  # Patient's nationality code.
    ma_dantoc: str  # Patient's ethnicity code.
    ma_nghe_nghiep: str  # Patient's occupation code.
    dia_chi: str  # Patient's current residential address.
    matinh_cu_tru: str  # Province/city code of residence.
    mahuyen_cu_tru: str  # District code of residence.
    maxa_cu_tru: str  # Ward/commune code of residence.
    dien_thoai: str  # Contact phone number.
    ma_the_bhyt: str  # Health insurance card number(s), separated by ';'.
    ma_dkbd: (
        str  # Code(s) of the initial registration facility, separated by ';'.
    )
    gt_the_tu: str  # Health insurance card start date(s), separated by ';'.
    gt_the_den: str  # Health insurance card end date(s), separated by ';'.
    ngay_mien_cct: str  # Date of co-payment exemption (yyyymmddHHMM).
    ly_do_vv: str  # Reason for visit.
    ly_do_vnt: str  # Reason for inpatient admission.
    ma_ly_do_vnt: str  # Code for the reason for inpatient admission.
    chan_doan_vao: str  # Initial diagnosis upon admission.
    chan_doan_rv: str  # Final diagnosis at discharge.
    ma_benh_chinh: str  # Main disease code (ICD-10).
    ma_benh_kt: str  # Accompanying disease codes, separated by ';'.
    ma_benh_yhct: str  # Traditional medicine disease codes, separated by ';'.
    ma_pttt_qt: str  # International surgery/procedure codes (ICD-9 CM), separated by ';'.
    ma_doituong_kcb: str  # Patient category code.
    ma_noi_di: str  # Code of the transferring facility.
    ma_noi_den: str  # Code of the receiving facility.
    ma_tai_nan: int  # Accident/injury code.
    ngay_vao: str  # Admission date and time (yyyymmddHHMM).
    ngay_vao_noi_tru: str  # Inpatient admission order time (yyyymmddHHMM).
    ngay_ra: str  # Discharge date and time (yyyymmddHHMM).
    giay_chuyen_tuyen: str  # Referral or follow-up appointment slip number.
    so_ngay_dtri: int  # Actual number of treatment days.
    pp_dieu_tri: str  # Treatment method.
    ket_qua_dtri: int  # Treatment outcome code (1: Cured, 2: Improved, ...).
    ma_loai_rv: int  # Discharge type code (1: Discharged, 2: Transferred, ...).
    ghi_chu: str  # Doctor's notes/instructions.
    ngay_ttoan: str  # Payment date and time (yyyymmddHHMM).
    t_thuoc: str  # Total cost of medications.
    t_vtyt: str  # Total cost of medical supplies.
    t_tongchi_bv: str  # Total cost at the hospital.
    t_tongchi_bh: str  # Total cost covered by health insurance.
    t_bntt: str  # Total amount paid by the patient out-of-pocket.
    t_bncct: str  # Total amount co-paid by the patient.
    t_bhtt: str  # Total amount requested for insurance reimbursement.
    t_nguonkhac: str  # Total amount paid by other sources.
    t_bhtt_gdv: str  # Amount paid by insurance outside of per-case payment.
    nam_qt: int  # Fiscal year of settlement.
    thang_qt: int  # Fiscal month of settlement.
    ma_loai_kcb: int  # Type of medical care code.
    ma_khoa: str  # Department/ward codes, separated by ';'.
    ma_cskcb: str  # Code of the treating healthcare facility.
    ma_khuvuc: str  # Area code from health insurance card (K1, K2, K3).
    can_nang: str  # Patient's weight (kg).
    can_nang_con: str  # Newborn's weight (grams), separated by ';'.
    nam_nam_lien_tuc: str  # Date of 5 consecutive years of insurance participation (yyyymmdd).
    ngay_tai_kham: str  # Follow-up appointment date(s), separated by ';'.
    ma_hsba: str  # Medical record number.
    ma_ttdv: str  # Medical ID of the head of the facility.
    du_phong: str  # Reserved field.


class ChiTietThuoc(TypedDict, total=False):
    """Represents detailed medication information for a treatment episode."""

    ma_lk: str  # Foreign key linking to KcbTongHop.
    stt: int  # Sequential number of the medication in the data submission.
    ma_thuoc: str  # Active ingredient/medication code.
    ma_pp_chebien: str  # Processing method code for traditional herbs.
    ma_cskcb_thuoc: (
        str  # Facility code that supplied/transferred special medication.
    )
    ma_nhom: int  # Cost group code.
    ten_thuoc: str  # Medication name.
    don_vi_tinh: str  # Smallest unit of measure.
    ham_luong: str  # Medication strength/concentration.
    duong_dung: str  # Route of administration code.
    dang_bao_che: str  # Pharmaceutical form.
    lieu_dung: str  # Dosage.
    cach_dung: str  # Instructions for use.
    so_dang_ky: str  # Marketing authorization number.
    tt_thau: str  # Bidding information for the medication.
    pham_vi: int  # Insurance coverage scope (1: Covered, 2: Not covered, 3: Special).
    tyle_tt_bh: int  # Insurance payment rate (%).
    so_luong: str  # Quantity of medication used.
    don_gia: str  # Unit price of the medication.
    thanh_tien_bv: str  # Total cost according to hospital price.
    thanh_tien_bh: str  # Total cost covered by insurance.
    t_nguonkhac_nsnn: str  # Amount supported by state budget.
    t_nguonkhac_vtnn: str  # Amount supported by foreign organizations.
    t_nguonkhac_vttn: str  # Amount supported by domestic organizations.
    t_nguonkhac_cl: str  # Amount supported by other sources.
    t_nguonkhac: str  # Total amount from other sources.
    muc_huong: int  # Insurance benefit level (%).
    t_bntt: str  # Amount paid by the patient out-of-pocket.
    t_bncct: str  # Amount co-paid by the patient.
    t_bhtt: str  # Amount requested for insurance reimbursement.
    ma_khoa: str  # Code of the prescribing department.
    ma_bac_si: str  # Medical ID of the prescribing doctor.
    ma_dich_vu: str  # Related technical service code (if any).
    ngay_yl: str  # Date and time of medical order (yyyymmddHHmm).
    ma_pttt: (
        int  # Payment method code (1: Fee-for-service, 2: Per-diem, 3: DRG).
    )
    nguon_ctra: int  # Payment source code (1: Insurance, 2: Project, ...).
    vet_thuong_tp: (
        int  # Flag for recurrent wound treatment for policy beneficiaries.
    )
    du_phong: str  # Reserved field.


class ChiTietDichVuVtyt(TypedDict, total=False):
    """Represents detailed services and medical supplies for a treatment episode."""

    ma_lk: str  # Foreign key linking to KcbTongHop.
    stt: int  # Sequential number of the service/supply.
    ma_dich_vu: str  # Code for technical service, consultation fee, or bed fee.
    ma_pttt_qt: str  # International surgery/procedure code.
    ma_vat_tu: str  # Medical supply code.
    ma_nhom: int  # Cost group code.
    goi_vtyt: str  # Supply package code for a single service use.
    ten_vat_tu: str  # Trade name of the medical supply.
    ten_dich_vu: str  # Name of the service, consultation, or bed type.
    ma_xang_dau: str  # Fuel type code for transportation costs.
    don_vi_tinh: str  # Unit of measure.
    pham_vi: int  # Insurance coverage scope.
    so_luong: str  # Quantity of service or supply used.
    don_gia_bv: str  # Unit price according to the hospital.
    don_gia_bh: str  # Unit price paid by insurance.
    tt_thau: str  # Bidding information for the supply.
    tyle_tt_dv: int  # Payment rate for special services (%).
    tyle_tt_bh: int  # Insurance payment rate (%).
    thanh_tien_bv: str  # Total cost according to hospital price.
    thanh_tien_bh: str  # Total cost paid by insurance.
    t_trantt: str  # Maximum payment for the supply package.
    muc_huong: int  # Insurance benefit level (%).
    t_nguonkhac_nsnn: str  # Amount supported by state budget.
    t_nguonkhac_vtnn: str  # Amount supported by foreign organizations.
    t_nguonkhac_vttn: str  # Amount supported by domestic organizations.
    t_nguonkhac_cl: str  # Amount supported by other sources.
    t_nguonkhac: str  # Total amount from other sources.
    t_bntt: str  # Amount paid by the patient out-of-pocket.
    t_bncct: str  # Amount co-paid by the patient.
    t_bhtt: str  # Amount requested for insurance reimbursement.
    ma_khoa: str  # Code of the department providing the service/supply.
    ma_giuong: str  # Bed code in the treatment ward.
    ma_bac_si: str  # Medical ID of the ordering healthcare professional.
    nguoi_thuc_hien: (
        str  # Medical ID of the performing healthcare professional.
    )
    ma_benh: str  # ICD-10 code requiring additional service.
    ma_benh_yhct: (
        str  # Traditional medicine disease code requiring additional service.
    )
    ngay_yl: str  # Date and time of medical order (yyyymmddHHMM).
    ngay_th_yl: str  # Date and time of order execution (yyyymmddHHMM).
    ngay_kq: str  # Date and time of result availability (yyyymmddHHMM).
    ma_pttt: int  # Payment method code.
    vet_thuong_tp: (
        int  # Flag for recurrent wound treatment for policy beneficiaries.
    )
    pp_vo_cam: int  # Anesthesia method code (1: General, 2: Regional, ...).
    vi_tri_th_dvkt: str  # Code for the location of surgery/procedure.
    ma_may: str  # Code of the machine/device used.
    ma_hieu_sp: str  # Product code of the medical supply.
    tai_su_dung: int  # Flag for reused medical supply (1: Yes).
    du_phong: str  # Reserved field.


class ChiTietCls(TypedDict, total=False):
    """Represents detailed paraclinical test results."""

    ma_lk: str  # Foreign key linking to KcbTongHop.
    stt: int  # Sequential number of the service.
    ma_dich_vu: str  # Paraclinical service code.
    ma_chi_so: str  # Code for the lab test, imaging, or functional exploration indicator.
    ten_chi_so: str  # Name of the indicator.
    gia_tri: str  # Result value of the indicator.
    don_vi_do: str  # Unit of measurement for the indicator.
    mo_ta: str  # Description by the interpreting specialist.
    ket_luan: str  # Conclusion by the interpreting specialist.
    ngay_kq: str  # Date and time of result availability (yyyymmddHHMM).
    ma_bs_doc_kq: str  # Medical ID of the interpreting specialist.
    du_phong: str  # Reserved field.


class DienBienLamSang(TypedDict, total=False):
    """Represents clinical progress notes."""

    ma_lk: str  # Foreign key linking to KcbTongHop.
    stt: int  # Sequential number of the record.
    dien_bien_ls: str  # Clinical progress and care notes.
    giai_doan_benh: str  # Stage of the disease (if any).
    hoi_chan: str  # Consultation results (if any).
    phau_thuat: str  # Description of surgery/procedure (if any).
    thoi_diem_dbls: str  # Time of clinical event (yyyymmddHHMM).
    nguoi_thuc_hien: str  # Medical ID of the recording person.
    du_phong: str  # Reserved field.


class HsbaHivAids(TypedDict, total=False):
    """Represents HIV/AIDS-specific medical record information."""

    ma_lk: str  # Foreign key linking to KcbTongHop. (PRIMARY KEY)
    ma_the_bhyt: str  # Patient's health insurance card number.
    so_cccd: str  # National ID/Passport number.
    ngaykd_hiv: str  # Date of HIV confirmation (yyyymmdd).
    bddt_arv: str  # Date of first ARV treatment (yyyymmdd).
    ma_phac_do_dieu_tri_bd: str  # Initial ARV treatment regimen code.
    ma_bac_phac_do_bd: int  # Tier of the initial regimen (1, 2, 3).
    ma_lydo_dtri: (
        int  # Reason for treatment registration (1: New, 2: Transfer, ...).
    )
    loai_dtri_lao: int  # Type of tuberculosis treatment (0: None, 1: Latent, 2: Active, ...).
    phacdo_dtri_lao: int  # Tuberculosis treatment regimen code.
    ngaybd_dtri_lao: str  # Start date of TB treatment (yyyymmdd).
    ngaykt_dtri_lao: str  # End date of TB treatment (yyyymmdd).
    ma_lydo_xntl_vr: int  # Reason for viral load test (1: Routine, 2: Suspected failure, ...).
    ngay_xn_tlvr: str  # Date of viral load sample collection (yyyymmdd).
    kq_xntl_vr: int  # HIV viral load test result code.
    ngay_kq_xn_tlvr: str  # Date of viral load result availability (yyyymmdd).
    ma_loai_bn: int  # Patient type (1: HIV-infected, 2: Exposed infant, ...).
    ma_tinh_trang_dk: str  # Patient status (1: Infant < 18mo, 2: Exposed, ...).
    lan_xn_pcr: int  # PCR test number (1, 2, 3).
    ngay_xn_pcr: str  # Date of PCR test (yyyymmdd).
    ngay_kq_xn_pcr: str  # Date of PCR result (yyyymmdd).
    ma_kq_xn_pcr: int  # PCR test result code (0: Negative, 1: Positive).
    ngay_nhan_tt_mang_thai: (
        str  # Date pregnancy information was received (yyyymmdd).
    )
    ngay_bat_dau_dt_ctx: (
        str  # Start date of Cotrimoxazole (CTX) treatment (yyyymmdd).
    )
    ma_xu_tri: str  # Management codes (1: ARV, 2: TB treatment, ...), separated by ';'.
    ngay_bat_dau_xu_tri: str  # Start date of ARV treatment episode (yyyymmdd).
    ngay_ket_thuc_xu_tri: str  # End date of ARV treatment episode (yyyymmdd).
    ma_phac_do_dieu_tri: str  # Treatment regimen code for the episode.
    ma_bac_phac_do: int  # Regimen tier for the episode (1, 2, 3).
    so_ngay_cap_thuoc_arv: int  # Number of days of ARV supplied.
    du_phong: str  # Reserved field.


class GiayRaVien(TypedDict, total=False):
    """Represents a hospital discharge certificate."""

    ma_lk: str  # Foreign key linking to KcbTongHop. (PRIMARY KEY)
    so_luu_tru: str  # Medical record archival number.
    ma_yte: str  # Medical ID, same as patient ID.
    ma_khoa_rv: str  # Code of the discharging department.
    ngay_vao: str  # Admission time (yyyymmddHHMM).
    ngay_ra: str  # Discharge time (yyyymmddHHMM).
    ma_dinh_chi_thai: int  # Pregnancy termination code (1: Yes, 0: No).
    nguyennhan_dinhchi: str  # Reason for pregnancy termination.
    thoigian_dinhchi: str  # Time of pregnancy termination (yyyymmddHHMM).
    tuoi_thai: int  # Gestational age in weeks.
    chan_doan_rv: str  # Discharge diagnosis.
    pp_dieutri: str  # Treatment method.
    ghi_chu: str  # Notes (for social security purposes).
    ma_ttdv: str  # Medical ID of the head of the facility.
    ma_bs: str  # Medical ID of the Head of Department.
    ten_bs: str  # Full name of the Head of Department.
    ngay_ct: str  # Date of certificate issuance (yyyymmdd).
    ma_cha: str  # Father's medical ID (if patient < 16 years).
    ma_me: str  # Mother's medical ID (if patient < 16 years).
    ma_the_tam: str  # Temporary insurance card number for child or organ donor.
    ho_ten_cha: str  # Father's full name.
    ho_ten_me: str  # Mother's full name.
    so_ngay_nghi: int  # Number of days of outpatient leave after discharge.
    ngoaitru_tungay: str  # Start date of outpatient leave (yyyymmdd).
    ngoaitru_denngay: str  # End date of outpatient leave (yyyymmdd).


class TomTatHsba(TypedDict, total=False):
    """Represents a summary of the medical record."""

    ma_lk: str  # Foreign key linking to KcbTongHop. (PRIMARY KEY)
    ma_loai_kcb: int  # Type of care (02: Outpatient, 03: Inpatient, ...).
    ho_ten_cha: str  # Father's full name (if applicable).
    ho_ten_me: str  # Mother's full name (if applicable).
    nguoi_giam_ho: str  # Guardian's full name (if applicable).
    don_vi: str  # Name of the patient's employer.
    ngay_vao: str  # Admission date and time (yyyymmddHHMM).
    ngay_ra: str  # Discharge date and time (yyyymmddHHMM).
    chan_doan_vao: str  # Initial diagnosis.
    chan_doan_rv: str  # Final diagnosis.
    qt_benhly: str  # Pathological process and clinical course.
    tomtat_kq: str  # Summary of significant paraclinical results.
    pp_dieutri: str  # Treatment method.
    ngay_sinhcon: str  # Date of birth of the child (if child died after birth).
    ngay_conchet: str  # Date of child's death (if child died after birth).
    so_conchet: int  # Number of deceased children (if child died after birth).
    ket_qua_dtri: int  # Treatment outcome code (1: Cured, 2: Improved, ...).
    ghi_chu: str  # Notes (e.g., parent/guardian name for special cases).
    ma_ttdv: str  # Medical ID of the head of the facility.
    ngay_ct: str  # Date of summary issuance (yyyymmdd).
    ma_the_tam: str  # Temporary insurance card number for child or organ donor.
    du_phong: str  # Reserved field.


class GiayChungSinh(TypedDict, total=False):
    """Represents a birth certificate."""

    ma_lk: str  # Foreign key linking to the mother's treatment episode.
    so: str  # Certificate number.
    ma_bhxh_nnd: str  # Social security number of the mother/guardian.
    ma_the_nnd: str  # Health insurance card number of the mother/guardian.
    ho_ten_nnd: str  # Full name of the mother/guardian.
    ngaysinh_nnd: str  # Date of birth of the mother/guardian (yyyymmdd).
    ma_dantoc_nnd: str  # Ethnicity code of the mother/guardian.
    so_cccd_nnd: str  # National ID/Passport number of the mother/guardian.
    ngaycap_cccd_nnd: str  # Issue date of ID (yyyymmdd).
    noicap_cccd_nnd: str  # Issuing authority of ID.
    noi_cu_tru_nnd: str  # Residential address of the mother/guardian.
    ma_quoctich: str  # Nationality code of the mother/guardian.
    matinh_cu_tru: str  # Province/city code of residence.
    mahuyen_cu_tru: str  # District code of residence.
    maxa_cu_tru: str  # Ward/commune code of residence.
    ho_ten_cha: str  # Father's full name.
    ma_the_tam: str  # Child's temporary health insurance card number.
    ho_ten_con: str  # Child's intended name.
    gioi_tinh_con: int  # Child's gender (1: Male, 2: Female, 3: Undetermined).
    so_con: int  # Number of children in this birth.
    lan_sinh: int  # Parity (number of births including this one).
    so_con_song: int  # Number of living children.
    can_nang_con: int  # Child's weight (grams).
    ngay_sinh_con: str  # Child's date and time of birth (yyyymmddHHMM).
    noi_sinh_con: str  # Place of birth.
    tinh_trang_con: str  # Child's condition at time of certificate issuance.
    sinhcon_phauthuat: int  # Birth by surgery (1: Yes, 0: No).
    duoi32tuan_sinhcon: int  # Premature birth before 32 weeks (1: Yes, 0: No).
    ghi_chu: str  # Notes on surgery or premature birth.
    nguoi_do_de: str  # Name of the birth attendant.
    nguoi_ghi_phieu: str  # Name of the person who filled out the form.
    ngay_ct: str  # Date of certificate issuance (yyyymmdd).
    quyen_so: str  # Certificate book number.
    ma_ttdv: str  # Medical ID of the head of the facility.


@dataclass
class GiayCnNghiDuongThai(TypedDict, total=False):
    """Represents a certificate for maternity leave for recuperation."""

    ma_lk: str  # Foreign key linking to KcbTongHop.
    so_seri: str  # Serial number of the certificate.
    so_ct: str  # Internal document number.
    so_ngay: int  # Number of leave days.
    don_vi: str  # Beneficiary's employer name.
    chan_doan_rv: str  # Diagnosis, must specify "dưỡng thai" (recuperation).
    tu_ngay: str  # Start date of leave (yyyymmdd).
    den_ngay: str  # End date of leave (yyyymmdd).
    ma_ttdv: str  # Medical ID of the head of the facility.
    ten_bs: str  # Full name of the signing doctor.
    ma_bs: str  # Medical ID of the signing doctor.
    ngay_ct: str  # Date of certificate issuance (yyyymmdd).


class GiayCnNghiViecBhxh(TypedDict, total=False):
    """Represents a certificate for sick leave for social security benefits."""

    ma_lk: str  # Foreign key linking to KcbTongHop.
    so_seri: str  # Unique serial number of the certificate.
    so_ct: str  # Internal document number.
    so_kcb: str  # Internal medical visit number.
    don_vi: str  # Beneficiary's employer name.
    ma_bhxh: str  # Patient's social security number.
    ma_the_bhyt: str  # Patient's health insurance card number.
    chan_doan_rv: str  # Diagnosis.
    pp_dieutri: str  # Treatment method.
    ma_dinh_chi_thai: int  # Pregnancy termination code (1: Yes, 0: No).
    nguyennhan_dinhchi: str  # Reason for pregnancy termination.
    tuoi_thai: int  # Gestational age (weeks).
    so_ngay_nghi: int  # Number of leave days.
    tu_ngay: str  # Start date of leave (yyyymmdd).
    den_ngay: str  # End date of leave (yyyymmdd).
    ho_ten_cha: str  # Father's name (if patient < 7 years).
    ho_ten_me: str  # Mother's name (if patient < 7 years).
    ma_ttdv: str  # Medical ID of the head of the facility.
    ma_bs: str  # Medical ID of the signing doctor.
    ngay_ct: str  # Date of certificate issuance (yyyymmdd).
    ma_the_tam: str  # Temporary health insurance card number.
    mau_so: str  # Form number, defaults to CT07.


class GiamDinhYKhoa(TypedDict, total=False):
    """Represents a medical assessment record."""

    id: int  # Auto-incrementing primary key.
    nguoi_chu_tri: str  # Name of the assessment council's chairperson.
    chuc_vu: int  # Chairperson's position (1: Chairman, 2: Acting).
    ngay_hop: str  # Date of the council meeting (yyyymmdd).
    ho_ten: str  # Full name of the person being assessed.
    ngay_sinh: str  # Date of birth of the assessed person (yyyymmdd).
    so_cccd: str  # National ID/Passport number.
    ngay_cap_cccd: str  # Issue date of ID (yyyymmdd).
    noi_cap_cccd: str  # Issuing authority of ID.
    dia_chi: str  # Residential address.
    matinh_cu_tru: str  # Province/city code.
    mahuyen_cu_tru: str  # District code.
    maxa_cu_tru: str  # Ward/commune code.
    ma_bhxh: str  # Social security number.
    ma_the_bhyt: str  # Health insurance card number.
    nghe_nghiep: str  # Occupation.
    dien_thoai: str  # Phone number.
    ma_doi_tuong: str  # Assessment subject code (e.g., occupational disease).
    kham_giam_dinh: (
        int  # Assessment type code (1: First-time, 2: Re-assessment, ...).
    )
    so_bien_ban: str  # Sequence number in the meeting minutes.
    tyle_ttct_cu: int  # Previous disability percentage (%).
    dang_huong_che_do: str  # Codes of current benefits, separated by ';'.
    ngay_chung_tu: str  # Document date (yyyymmdd).
    so_giay_gioi_thieu: str  # Referral letter number.
    ngay_de_nghi: str  # Request date (yyyymmdd).
    ma_donvi: str  # Code of the referring agency.
    gioi_thieu_cua: str  # Full name of the referring agency.
    ket_qua_kham: str  # Examination results from the council.
    so_van_ban_can_cu: str  # Reference document number.
    tyle_ttct_moi: int  # Current disability percentage (%).
    tong_tyle_ttct: int  # Total disability percentage.
    dang_khuyettat: int  # Type of disability code.
    muc_do_khuyettat: int  # Level of disability code.
    de_nghi: str  # Recommendations.
    duoc_xacdinh: str  # Determination notes.
    du_phong: str  # Reserved field.


class VN_MOH(TypedDict, total=False):
    tong_hop: KcbTongHop
    chi_tiet_thuoc: list[ChiTietThuoc]
    chi_tiet_dich_vu_vtyt: list[ChiTietDichVuVtyt]
    chi_tiet_cls: list[ChiTietCls]
    dien_bien_lam_sang: list[DienBienLamSang]
    hsba_hiv_aids: HsbaHivAids
    giay_ra_vien: GiayRaVien
    tom_tat_hsba: TomTatHsba
    giay_chung_sinh: GiayChungSinh
    giay_cn_nghi_duong_thai: GiayCnNghiDuongThai
    giay_cn_nghi_viec_bhxh: GiayCnNghiViecBhxh
    giam_dinh_y_khoa: GiamDinhYKhoa


def toDateTime(ee: Optional[str]) -> Optional[str]:
    """Converts a string representing a date and time in the format 'YYYYMMDDHHMM' to a formatted string 'YYYY/MM/DD HH:MM'.

    If the input string is shorter than 12 characters, it is right-padded with zeros.
    If the input is None, returns None.

    Args:
        ee (Optional[str]): The date-time string to convert.

    Returns:
        Optional[str]: The formatted date-time string, or None if input is None.
    """
    if ee is None:
        return None
    ee = ee.ljust(12, "0")
    return datetime.strptime(ee, "%Y%m%d%H%M").strftime("%Y/%m/%d %H:%M")


def splitKhoaDieuTri(s: list[str]) -> list[str]:
    """Splits each string in the input list representing concatenated department codes into individual codes.

    Each code is assumed to start with 'K' followed by two digits. If an element in the input list is longer than 3 characters,
    it is split into multiple codes of the form 'Kxx' (where xx are two digits), starting from the second character.

    Args:
        s (list[str]): A list of strings, each representing one or more concatenated department codes.

    Returns:
        list[str]: A list of unique department codes extracted from the input.

    Examples:
        `splitKhoaDieuTri("K192021") == ["K19", "K20", "K21"]`
    """
    tmp = set(s)
    for i in range(len(s)):
        if len(s[i]) > 3:
            tmp.remove(s[i])
            for j in range(1, len(s[i]), 2):
                tmp.add("K" + s[i][j : j + 2])
    return list(tmp)


def toList(obj, none_empty=True) -> list:
    if obj is None and none_empty:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, str) or isinstance(obj, dict):
        return [obj]
    if isinstance(obj, Iterable):
        return list(obj)
    return [obj]
