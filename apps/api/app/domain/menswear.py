"""Reviewed menswear navigation from the three user supplied category images."""

MENSWEAR_ROOT = "nam"
# Group ID, label, then leaf ID / label / accepted search names.
MENSWEAR_GROUPS = (
    (
        "nam-ao",
        "Áo",
        (
            ("nam-ao-pull", "Áo pull", ("áo pull", "áo thun", "áo phông")),
            ("nam-polo", "Polo", ("polo", "áo polo")),
            ("nam-ao-so-mi", "Áo sơ mi", ("áo sơ mi",)),
            ("nam-tanktop", "Tanktop", ("tanktop", "tank top", "áo ba lỗ")),
            ("nam-cardigan-khoac-nhe", "Cardigan & khoác nhẹ", ("cardigan", "khoác nhẹ")),
            ("nam-ao-ni-len", "Áo nỉ & len", ("áo nỉ", "áo len", "áo hoodie")),
            ("nam-ao-khoac", "Áo khoác", ("áo khoác", "áo phao")),
        ),
    ),
    (
        "nam-quan",
        "Quần",
        (
            ("nam-quan-lung", "Quần lửng", ("quần lửng", "quần short", "quần đùi")),
            ("nam-quan-au-vai", "Quần âu vải", ("quần âu", "quần tây", "quần vải")),
            ("nam-quan-khaki", "Quần khaki", ("quần khaki", "quần kaki")),
            ("nam-quan-jeans", "Quần jeans", ("quần jeans", "quần jean", "quần bò")),
            ("nam-quan-ni", "Quần nỉ", ("quần nỉ",)),
        ),
    ),
    (
        "nam-phu-kien",
        "Phụ kiện",
        (
            ("nam-vong-charm", "Vòng tay - vòng cổ - charm", ("vòng tay", "vòng cổ", "charm")),
            ("nam-mu", "Mũ", ("mũ", "nón")),
            ("nam-balo-tui", "Balo - túi", ("balo", "ba lô", "balô", "túi")),
            ("nam-day-lung-xich", "Dây lưng - xích", ("dây lưng", "thắt lưng", "xích")),
            ("nam-khan-gang-tay", "Khăn - găng tay", ("khăn", "găng tay")),
            ("nam-giay-tat", "Giày - tất", ("giày", "tất", "vớ")),
            ("nam-kinh-mat", "Kính mắt", ("kính mắt", "kính râm")),
        ),
    ),
)
