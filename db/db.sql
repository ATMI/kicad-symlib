create type library_type as enum ('symbol', 'footprint');

alter type library_type owner to kicad_admin;

create table library
(
    id    serial
        constraint library_id
            primary key,
    type  library_type not null,
    alias varchar(63)  not null,
    path  varchar(255),
    constraint library_alias
        unique (type, alias),
    constraint library_path
        unique (type, path)
);

alter table library
    owner to kicad_admin;

create table package
(
    id   serial
        constraint package_id
            primary key,
    name varchar(63)
        constraint package_name
            unique
);

comment on table package is 'Recognizable package name';

alter table package
    owner to kicad_admin;

create table footprint
(
    id         serial
        constraint footprint_pk
            primary key,
    name       varchar(63) not null
        constraint footprint_name
            unique,
    library_id integer     not null
        constraint footprint_library_id_fk
            references library
            on update cascade on delete cascade,
    package_id integer
        constraint footprint_package_id_fk
            references package
);

alter table footprint
    owner to kicad_admin;

grant select on footprint to kicad_user;

create table symbol
(
    id         serial
        constraint symbol_pk
            primary key,
    name       varchar(63) not null
        constraint symbol_name
            unique,
    library_id integer     not null
        constraint symbol_library_id_fk
            references library
            on update cascade on delete cascade
);

alter table symbol
    owner to kicad_admin;

grant select on symbol to kicad_user;

create table part
(
    partnumber   varchar               not null
        constraint part_pk
            primary key,
    symbol_id    integer               not null
        constraint part_symbol_id_fk
            references symbol,
    footprint_id integer               not null
        constraint part_footprint_id_fk
            references footprint,
    value        varchar(63),
    description  varchar(255),
    datasheet    varchar(4095),
    exclude_bom  boolean default false not null,
    exclude_pcb  boolean default false not null,
    lcsc_num     varchar(63),
    chipdip_num  bigint
);

alter table part
    owner to kicad_admin;

create unique index part_chipdip_num_uindex
    on part (chipdip_num);

create index part_value_index
    on part (value);

create unique index part_lcsc_num_uindex
    on part (lcsc_num);

create view kicad
            (partnumber, symbol, footprint, package, value, description, datasheet, lcsc_num, chipdip_num, exclude_bom,
             exclude_pcb)
as
SELECT e.partnumber,
	CONCAT(sl.alias, ':', s.name) AS symbol,
	CONCAT(fl.alias, ':', f.name) AS footprint,
	p.name AS package,
	e.value,
	e.description,
	e.datasheet,
	e.lcsc_num,
	e.chipdip_num,
	e.exclude_bom,
	e.exclude_pcb
FROM part e
	LEFT JOIN symbol s ON e.symbol_id = s.id
	LEFT JOIN footprint f ON e.footprint_id = f.id
	LEFT JOIN package p ON f.package_id = p.id
	LEFT JOIN library fl ON f.library_id = fl.id AND fl.type = 'footprint'::library_type
	LEFT JOIN library sl ON s.library_id = sl.id AND sl.type = 'symbol'::library_type;

alter table kicad
    owner to kicad_admin;
