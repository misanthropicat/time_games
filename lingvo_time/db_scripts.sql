drop table if exists lingvo_exercises;
drop table if exists math_exercises;
drop table if exists runs;

create table lingvo_exercises (
    task_id primary key not null,
    run_id not null,
    word varchar(100),
    spaced integer,
    task_created real,
    last_updated real,
    answer varchar(1),
    foreign key (run_id) references runs(run_id)
);

create table runs (
    run_id not null primary key,
    run_created real,
    runtime real,
    play_time_sec integer,
    game_type varchar(25),
    complexity real
);

create table math_exercises (
    task_id not null primary key,
    run_id not null,
    task varchar(100),
    expected integer,
    task_created real,
    last_updated real,
    result integer,
    foreign key (run_id) references runs(run_id)
)