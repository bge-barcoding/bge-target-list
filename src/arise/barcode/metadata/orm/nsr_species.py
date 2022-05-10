from arise.barcode.metadata.orm.imports import *


class NsrSpecies(Base):
    __tablename__ = 'nsr_species'

    species_id = Column(Integer, primary_key=True)
    nsr_id = Column(String)
    canonical_name = Column(String)

    def __repr__(self):
        return "<NsrSpecies(species_name='%s')>" % (
                         self.species_name)







