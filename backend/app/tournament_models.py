from datetime import date
from decimal import Decimal
from sqlalchemy import (
    CheckConstraint,
    Float,
    String,
    Integer,
    Date,
    Numeric,
    Boolean,
    Column,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ==============================
# BASE
# ==============================

class TournamentBase(DeclarativeBase):
    pass

# ==============================
# ATHLETES
# ==============================

class Athlete(TournamentBase):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    second_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(7), nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    weight_fact: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    rank_kyu: Mapped[str | None] = mapped_column(String(5), nullable=False)
    rank_sport: Mapped[str | None] = mapped_column(String(5), nullable=False)
    # club: Mapped[str] = mapped_column(String(150), nullable=False)
    # coach: Mapped[str] = mapped_column(String(150), nullable=False)
    # is_present: Mapped[bool] = mapped_column(Boolean, default=False)
    # is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registration_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    club = relationship("Club")
    coach = relationship("Coach")

    club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    coach_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("coaches.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

# ==============================
# CATEGORIES
# ==============================

class Category(TournamentBase):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str] = mapped_column(String(7), nullable=True)
    age_min: Mapped[int] = mapped_column(Integer, nullable=False)
    age_max: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_min: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    weight_max: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "discipline IN ('kata', 'kumite', 'kata-group')",
            name="check_category_discipline"
        ),
        CheckConstraint(
            "age_min < age_max",
            name="check_category_age"
        ),
        CheckConstraint(
            "discipline = 'kumite' OR "
            "(weight_min IS NULL AND weight_max IS NULL)",
            name="check_kata_without_weight"
        ),
        CheckConstraint(
            "weight_min IS NULL OR weight_max IS NULL "
            "OR weight_min < weight_max ",
            name="check_category_weight"
        ),
    )

# ==============================
# ATHLETE-CATEGORY ASSOCIATION
# ==============================

class AthleteCategory(TournamentBase):
    __tablename__ = "athlete_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "athlete_id",
            "category_id",
            name="uq_athlete_category"
        ),
    )

# ==============================
# CLUBS AND COACHES
# ==============================

class Club(TournamentBase):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)

class Coach(TournamentBase):
    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    second_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "last_name",
            "first_name",
            "second_name",
            "club_id",
            name="uq_coach_club"
        ),
    )

# ==============================
# KATA GROUPS
# ==============================

class KataGroup(TournamentBase):
    __tablename__ = "kata_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "name",
            "category_id",
            name="uq_kata_group_category"
        ),
    )

class KataGroupAthlete(TournamentBase):
    __tablename__ = "kata_group_athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    kata_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("kata_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    athlete_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "kata_group_id",
            "athlete_id",
            name="uq_kata_group_athlete"
        ),
    )

# ==============================
# CATEGORY DISTRIBUTION
# ==============================

class CategoryDistribution(TournamentBase):
    __tablename__ = "category_distributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draw_order: Mapped[int] = mapped_column(Integer, nullable=True)

    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    athlete_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    kata_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("kata_groups.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "athlete_id",
            name="uq_category_distributions_athlete"
        ),
        UniqueConstraint(
            "category_id",
            "kata_group_id",
            name="uq_category_distributions_kata_group"
        ),
        CheckConstraint(
            """
            (athlete_id IS NOT NULL AND kata_group_id IS NULL)
            OR
            (athlete_id IS NULL AND kata_group_id IS NOT NULL)
            """,
            name="ck_category_distribution_one_participant"
        )
    )

# ==============================
# UNDISTRIBUTION / EXCLUSIONS
# ==============================

class Undistribution(TournamentBase):
    __tablename__ = "undistributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    athlete_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

# ==============================
# KUMITE DRAW
# ==============================

class KumiteDrawEntry(TournamentBase):
    __tablename__ = "kumite_draw_entries"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    category_id: Mapped[int] = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    athlete_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    draw_position: Mapped[int] = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "athlete_id",
            name="uq_kumite_draw_category_athlete"
        ),
        UniqueConstraint(
            "category_id",
            "draw_position",
            name="uq_kumite_draw_category_position"
        ),
    )

class KumiteDrawMatch(TournamentBase):
    __tablename__ = "kumite_draw_matches"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    round_number: Mapped[int] = Column(Integer, nullable=False)
    match_number: Mapped[int] = Column(Integer, nullable=False)

    athlete1_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True
    )
    athlete2_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True
    )
    winner_athlete_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True
    )

    athlete1 = relationship("Athlete", foreign_keys=[athlete1_id])
    athlete2= relationship("Athlete", foreign_keys=[athlete2_id])

    match_type: Mapped[str] = Column(String(20), nullable=False, default="regular")
    status: Mapped[str] = Column(String(20), nullable=False, default="pending")

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "round_number",
            "match_number",
            name="uq_kumite_match_round"
        ),
    )

# ==============================
# TATAMI
# ==============================

class KumiteTatami(TournamentBase):
    __tablename__ = "kumite_tatamis"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(50), nullable=False, unique=True)
    number: Mapped[int] = Column(Integer, nullable=False, unique=True)

class KataTatami(TournamentBase):
    __tablename__ = "kata_tatamis"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(50), nullable=False, unique=True)
    number: Mapped[int] = Column(Integer, nullable=False, unique=True)


class CategoryTatami(TournamentBase):
    __tablename__ = "category_tatamis"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    position: Mapped[int] = Column(Integer, nullable=False, default=0)

    category_id: Mapped[int] = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    kata_tatami_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_tatamis.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    kumite_tatami_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kumite_tatamis.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

# ==============================
# MATCHES AND RESULTS
# ==============================

class BronzeMatchResult(TournamentBase):
    __tablename__ = "bronze_match_results"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    category_id: Mapped[int] = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    athlete1_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True
    )

    athlete2_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True
    )

    winner_athlete_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True
    )

    athlete1 = relationship("Athlete", foreign_keys=[athlete1_id])
    athlete2 = relationship("Athlete", foreign_keys=[athlete2_id])

    status: Mapped[str] = Column(String(20), nullable=False, default="pending")

# ==============================
# KUMITE RESULTS
# ==============================

class KumiteResult(TournamentBase):
    __tablename__ = "kumite_results"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    athlete_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    place: Mapped[int] = Column(Integer, nullable=False)

    athlete = relationship("Athlete")
    category = relationship("Category")

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "athlete_id",
            name="uq_kumite_result_athlete"
        ),
        UniqueConstraint(
            "category_id",
            "place",
            name="uq_kumite_result_place"
        ),
    )

# ==============================
# KATA COMPETITION AND ROUNDS
# ==============================

class KataCompetition(TournamentBase):
    __tablename__ = "kata_competitions"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    status: Mapped[str] = Column(String(20), nullable=False, default="created")


class KataRound(TournamentBase):
    __tablename__ = "kata_rounds"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    competition_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    number: Mapped[int] = Column(Integer, nullable=False)
    round_type: Mapped[str] = Column(String(20), nullable=False, default="regular")
    status: Mapped[str] = Column(String(20), nullable=False, default="pending")
    source_round_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_rounds.id", ondelete="CASCADE"),
        nullable=True
    )

    advancement_limit: Mapped[int] = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "number",
            name="uq_kata_round_competition_number"
        ),
    )


# ==============================
# KATA ROUND PARTICIPANTS
# ==============================

class KataRoundParticipant(TournamentBase):
    __tablename__ = "kata_round_participants"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    round_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    athlete_id: Mapped[int] = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    kata_group_id: Mapped[int] = Column(
        Integer,
        ForeignKey("kata_groups.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    position: Mapped[int] = Column(Integer, nullable=False)
    total_score: Mapped[float] = Column(Float, nullable=True)

    __table_args__ = (
        CheckConstraint(
            """
            (athlete_id IS NOT NULL AND kata_group_id IS NULL)
            OR
            (athlete_id IS NULL AND kata_group_id IS NOT NULL)
            """,
            name="ck_kata_round_participant_one_type"
        ),
        UniqueConstraint(
            "round_id",
            "athlete_id",
            name="uq_kata_round_athlete"
        ),
        UniqueConstraint(
            "round_id",
            "kata_group_id",
            name="uq_kata_round_group"
        ),
    )


# ==============================
# KATA SCORES
# ==============================

class KataScore(TournamentBase):
    __tablename__ = "kata_scores"

    id = Column(Integer, primary_key=True, index=True)

    round_participant_id = Column(
        Integer,
        ForeignKey("kata_round_participants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    score1 = Column(Float, nullable=True)
    score2 = Column(Float, nullable=True)
    score3 = Column(Float, nullable=True)
    score4 = Column(Float, nullable=True)
    score5 = Column(Float, nullable=True)

    total_score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    min_score = Column(Float, nullable=True)

    is_confirmed = Column(Boolean, nullable=False, default=False)


# ==============================
# KATA COMPETITION RESULTS
# ==============================

class KataCompetitionResult(TournamentBase):
    __tablename__ = "kata_competition_results"

    id = Column(Integer, primary_key=True, index=True)

    competition_id = Column(
        Integer,
        ForeignKey("kata_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=True
    )

    kata_group_id = Column(
        Integer,
        ForeignKey("kata_groups.id", ondelete="CASCADE"),
        nullable=True
    )

    place = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(
            """
            (athlete_id IS NOT NULL AND kata_group_id IS NULL)
            OR
            (athlete_id IS NULL AND kata_group_id IS NOT NULL)
            """,
            name="ck_kata_result_one_type"
        ),
        UniqueConstraint(
            "competition_id",
            "athlete_id",
            name="uq_kata_result_athlete"
        ),
        UniqueConstraint(
            "competition_id",
            "kata_group_id",
            name="uq_kata_result_group"
        ),
        UniqueConstraint(
            "competition_id",
            "place",
            name="uq_kata_result_place"
        ),
    )
