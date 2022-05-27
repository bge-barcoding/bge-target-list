from arise.barcode.metadata.orm.imports import *


class Specimen(Base):
    __tablename__ = 'specimen'
    specimen_id = Column(Integer, primary_key=True, autoincrement=True)
    catalognum = Column(String, index=True)
    institution_storing = Column(String, index=True)
    identification_provided_by = Column(String, index=True)
    species_id = Column(Integer, ForeignKey('nsr_species.species_id'))

    barcodes = relationship('Barcode', backref=backref("specimen", cascade="all, delete"))

    # find or create specimen object
    @classmethod
    def match_specimen(cls, species_id, catalognum, institution_storing, identification_provided_by, session):
        specimen = session.query(Specimen).filter(Specimen.species_id == species_id, Specimen.catalognum == catalognum,
                                                  Specimen.institution_storing == institution_storing,
                                                  Specimen.identification_provided_by == identification_provided_by).first()
        if specimen is None:
            specimen = Specimen(species_id=species_id, catalognum=catalognum, institution_storing=institution_storing,
                                identification_provided_by=identification_provided_by)
            session.add(specimen)
            session.flush()
        return specimen

    def __repr__(self):
        return "<Specimen(name='%s')>" % (
                         self.specimen_id)
