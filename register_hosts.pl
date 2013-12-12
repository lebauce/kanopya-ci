use BaseDB;
use Harddisk;
use Entity::Host;
use Entity::ServiceProvider::Cluster;
use JSON;
use Kanopya::Tools::Register;
use TryCatch;
my $err;


try {
    require "/opt/kanopya/lib/common/Kanopya/Database.pm";
    Kanopya::Database::authenticate(login => "admin", password => "K4n0pY4");
}
catch($err) {
    use BaseDB;
    BaseDB->authenticate(login => "admin", password => "K4n0pY4");
}

my $json = '';
open (JSON, '<', '/vagrant/hosts.json');
while (<JSON>) {
    $json .= $_;
}

my $kanopya_cluster = Entity::ServiceProvider::Cluster->find(
                          hash => {
                              cluster_name => 'Kanopya'   
                          }
                      );

$kanopya_cluster->cluster_nameserver1("192.168.10.254");

my $physical_hoster = $kanopya_cluster->getHostManager();
my $hosts = decode_json($json);

for my $board (@{$hosts}) {
    Kanopya::Tools::Register->registerHost(board => $board);
}
