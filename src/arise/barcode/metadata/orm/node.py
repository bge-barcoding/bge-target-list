from arise.barcode.metadata.orm.imports import *


class Node(Base):

    # This constructor defines the equivalent of the below schema from DBTree, extended with a few
    # more NSR-specific fields:
    # create table node(
    #   id int not null,
    #   parent int,
    #   left int,
    #   right int,
    #   name varchar(20),
    #   length float,
    #   height float,
    #   primary key(id)
    # );
    # create index parent_idx on node(parent);
    # create index left_idx on node(left);
    # create index right_idx on node(right);
    # create index name_idx on node(name);

    __tablename__ = 'node'
    id = Column(Integer, primary_key=True)
    parent = Column(Integer)
    left = Column(Integer)
    right = Column(Integer)
    name = Column(String)
    length = Column(Float)
    height = Column(Float)
    tax_id = Column(Integer)
    rank = Column(String)
    species_id = Column(Integer, ForeignKey('nsr_species.species_id'), primary_key=True)

    def __repr__(self):
        return "<Node(name='%s')>" % (
                         self.name)
