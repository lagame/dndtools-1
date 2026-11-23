<?php
namespace dndtools\discussions\migrations;

class install_schema extends \phpbb\db\migration\migration
{
    static public function depends_on()
    {
        return ['\phpbb\db\migration\data\v330\v330'];
    }

    public function update_schema()
    {
        return ['add_tables' => [
            $this->table_prefix . 'dnd_record_topics' => [
                'COLUMNS' => [
                    'topic_id' => ['UINT', 0],
                    'record_kind' => ['VCHAR:40', ''],
                    'record_id' => ['UINT', 0],
                    'discussion_type' => ['VCHAR:20', ''],
                ],
                'PRIMARY_KEY' => 'topic_id',
                'KEYS' => ['record' => ['INDEX', ['record_kind', 'record_id']]],
            ],
        ]];
    }

    public function revert_schema()
    {
        return ['drop_tables' => [$this->table_prefix . 'dnd_record_topics']];
    }
}
